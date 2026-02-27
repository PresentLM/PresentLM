"""
Narration Generator - Creates structured spoken explanations for slides using LLM.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import openai

from ..utils.config import Config
from ..utils.benchmark import get_benchmark_tracker
from .slide_parser import Slide


@dataclass
class SlideNarration:
    """Narration for a single slide."""
    slide_number: int
    narration_text: str
    estimated_duration: float  # in seconds
    
    def to_dict(self) -> Dict:
        return {
            "slide_number": self.slide_number,
            "narration_text": self.narration_text,
            "estimated_duration": self.estimated_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SlideNarration':
        """Create SlideNarration from dictionary."""
        return cls(
            slide_number=data['slide_number'],
            narration_text=data['narration_text'],
            estimated_duration=data['estimated_duration']
        )


class NarrationGenerator:
    """Generate narration for slides using LLM."""
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, use_vision: Optional[bool] = None):
        """
        Initialize narration generator.
        
        Args:
            provider: LLM provider (openai, anthropic, google). Defaults to Config.
            model: Model name. Defaults to Config.
            use_vision: Whether to use vision models for image analysis. Defaults to Config.
        """
        self.provider = provider or Config.LLM_PROVIDER
        self.model = model or Config.LLM_MODEL
        self.use_vision = use_vision if use_vision is not None else Config.LLM_USE_VISION

        # Initialize client based on provider
        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        elif self.provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            except ImportError:
                raise ValueError("anthropic package not installed. Run: pip install anthropic")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def generate_narration(
        self, 
        slides: List[Slide],
        context: Optional[str] = None,
        style: str = "educational",
        mode: str = "slide_by_slide"  # New parameter to switch between modes ("slide_by_slide" or "continuous")
    ) -> List[SlideNarration]:
        """
        Generate narration for slides.

        Args:
            slides: List of parsed slides
            context: Additional context (lecture notes, documents)
            style: Narration style (educational, professional, casual)
            mode: Narration mode ("slide_by_slide" or "continuous")

        Returns:
            List of SlideNarration objects
        """
        # Start benchmarking
        benchmark = get_benchmark_tracker()
        timer_id = f"generate_narration_{id(self)}"
        benchmark.start_timer(timer_id)
        
        if mode == "continuous":
            narrations = self._generate_continuous_narration(slides, context, style)
        else:
            narrations = []
            for slide in slides:
                # Use vision for each slide if available
                narration_text = self._generate_single_narration(
                    slide,
                    context=context,
                    style=style,
                    previous_slides=slides[:slide.slide_number-1],
                )

                # Estimate duration (150 words per minute)
                word_count = len(narration_text.split())
                duration = (word_count / 150) * 60

                narrations.append(SlideNarration(
                    slide_number=slide.slide_number,
                    narration_text=narration_text,
                    estimated_duration=duration
                ))

                # Log vision usage
                if self.use_vision and slide.image_data:
                    print(f"✅ Slide {slide.slide_number}: Vision analysis used ({len(slide.image_data)/1024:.1f} KB image)")

        # End benchmarking
        duration = benchmark.end_timer(
            timer_id,
            component="NarrationGenerator",
            operation="generate_narration",
            metadata={
                "num_slides": len(slides),
                "model": self.model,
                "style": style,
                "mode": mode
            }
        )
        
        print(f"[BENCHMARK] NarrationGenerator.generate_narration: {duration:.2f}s for {len(narrations)} slides")
        
        return narrations

    def _generate_single_narration(
        self,
        slide: Slide,
        context: Optional[str],
        style: str,
        previous_slides: List[Slide],
    ) -> str:
        """Generate narration for a single slide with optional image analysis."""

        # Build prompt
        prompt = self._build_prompt(slide, context, style, previous_slides)

        # Call LLM based on provider, pass image if available and vision is enabled
        if self.provider == "openai":
            image_data = slide.image_data_compressed if (self.use_vision and slide.image_data_compressed) else None
            return self._generate_openai(prompt, image_data=image_data)
        elif self.provider == "anthropic":
            image_data = slide.image_data_compressed if (self.use_vision and slide.image_data_compressed) else None
            return self._generate_anthropic(prompt, image_data=image_data)

    def _generate_single_narration_with_visual_history(
        self,
        slide: Slide,
        context: Optional[str],
        style: str,
        previous_slides: List[Slide],
    ) -> str:
        """Generate narration with FULL VISUAL HISTORY - includes images from all previous slides.

        This provides better visual coherence in continuous mode by letting the LLM see
        all previous slide images, not just the current one.
        """

        # Build prompt
        prompt = self._build_prompt(slide, context, style, previous_slides)

        # Collect all images: previous slides + current slide
        all_images = []

        # Add previous slide images (up to last 3 for API limits)
        for prev_slide in previous_slides[-3:]:  # Last 3 slides for context
            if prev_slide.image_data:
                all_images.append({
                    'slide_number': prev_slide.slide_number,
                    'title': prev_slide.title,
                    'image_data': prev_slide.image_data
                })

        # Add current slide image
        if slide.image_data:
            all_images.append({
                'slide_number': slide.slide_number,
                'title': slide.title,
                'image_data': slide.image_data,
                'is_current': True
            })

        # Call LLM with multiple images
        if self.provider == "openai":
            return self._generate_openai_multimodal(prompt, all_images)
        elif self.provider == "anthropic":
            return self._generate_anthropic_multimodal(prompt, all_images)
        else:
            # Fallback to single image if provider doesn't support multimodal
            return self._generate_single_narration(slide, context, style, previous_slides)

    def _build_prompt(
        self,
        slide: Slide,
        context: Optional[str],
        style: str,
        previous_slides: List[Slide],
    ) -> str:
        """Build the prompt for narration generation."""

        # Add vision-specific instructions if image is present
        vision_instruction = ""
        if self.use_vision and slide.image_data:
            vision_instruction = """
The slide image is provided. Please analyze:
- Visual elements (diagrams, charts, images, graphics)
- Layout and design elements that convey meaning
- Text visible in the image that may not be captured in the content above
- Colors, icons, or visual metaphors that enhance understanding

Incorporate visual analysis into your narration naturally.
"""

        prompt = f"""You are generating a spoken narration for a presentation slide.

SLIDE {slide.slide_number}:
Title: {slide.title}
Content:
{slide.content}

{f"Speaker Notes: {slide.notes}" if slide.notes else ""}

{f"Additional Context: {context}" if context else ""}

{vision_instruction}

TASK:
Generate a natural, spoken explanation for this slide in a {style} style.
The narration should:
1. Explain what the slide shows and how it connects to the previous slide if relevant.
2. Avoid repeating information already covered in previous slides.
3. Provide new insights or details that build on the previous slides.
4. Be suitable for text-to-speech (avoid special characters, use natural speech).
5. Flow naturally from previous slides with clear transitions.
6. Be concise but complete (aim for 30-90 seconds when spoken).
{f"7. Describe and explain visual elements visible in the slide image." if self.use_vision and slide.image_data else ""}

Previous slides covered:
{self._summarize_previous_slides(previous_slides) if previous_slides else "This is the first slide."}


Generate ONLY the narration text, without any meta-commentary or labels.
"""
        return prompt

    def _summarize_previous_slides(self, slides: List[Slide]) -> str:
        """Create brief summary of previous slides for context."""
        if not slides:
            return "None"
        return "\n".join([f"- Slide {s.slide_number}: {s.title}" for s in slides[-3:]])

    def _generate_openai(self, prompt: str, image_data: Optional[bytes] = None) -> str:
        """Generate using OpenAI with optional vision support.

        Args:
            prompt: Text prompt
            image_data: Optional image bytes (JPEG/PNG) for vision models

        Returns:
            Generated narration text
        """
        messages = [
            {"role": "system", "content": "You are an expert presenter creating engaging spoken narrations for slides."}
        ]

        # If image data is provided and vision is enabled, use vision model
        if image_data and self.use_vision:
            # Encode image to base64
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Create multi-modal message with image
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "high"  # high/low/auto - high for detailed analysis
                        }
                    }
                ]
            })

            # Use vision-capable model (override if not already vision-capable)
            model = self.model if "vision" in self.model.lower() or "gpt-4" in self.model.lower() else "gpt-4-turbo"
        else:
            # Text-only message
            messages.append({
                "role": "user",
                "content": prompt
            })
            model = self.model

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=Config.LLM_TEMPERATURE,
            max_tokens=Config.LLM_MAX_TOKENS
        )
        return response.choices[0].message.content.strip()

    def _generate_openai_multimodal(self, prompt: str, images: List[Dict]) -> str:
        """Generate using OpenAI with MULTIPLE images (previous slides + current).

        Args:
            prompt: Text prompt
            images: List of dicts with 'slide_number', 'title', 'image_data', and optional 'is_current'

        Returns:
            Generated narration text
        """
        import base64

        messages = [
            {"role": "system", "content": "You are an expert presenter creating engaging spoken narrations for slides."}
        ]

        # Build content with all images
        content = []

        # Add text prompt first
        enhanced_prompt = prompt
        if len(images) > 1:
            # Enhance prompt to mention previous slide images
            prev_count = sum(1 for img in images if not img.get('is_current', False))
            enhanced_prompt = f"""IMPORTANT: You are seeing {len(images)} slide images:
- {prev_count} previous slide(s) for visual context
- 1 current slide that you're narrating

Use the previous slides' visual elements to create coherent transitions and avoid repeating visual descriptions.

{prompt}"""

        content.append({
            "type": "text",
            "text": enhanced_prompt
        })

        # Add all images with labels
        for img in images:
            is_current = img.get('is_current', False)
            label = f"[CURRENT SLIDE {img['slide_number']}]" if is_current else f"[Previous Slide {img['slide_number']}: {img['title']}]"

            # Add label
            content.append({
                "type": "text",
                "text": label
            })

            # Add image
            image_base64 = base64.b64encode(img['image_data']).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}",
                    "detail": "high" if is_current else "low"  # High detail for current, low for previous
                }
            })

        messages.append({
            "role": "user",
            "content": content
        })

        # Use vision-capable model
        model = self.model if "vision" in self.model.lower() or "gpt-4" in self.model.lower() else "gpt-4-turbo"

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=Config.LLM_TEMPERATURE,
            max_tokens=Config.LLM_MAX_TOKENS
        )
        return response.choices[0].message.content.strip()

    def _generate_anthropic(self, prompt: str, image_data: Optional[bytes] = None) -> str:
        """Generate using Anthropic Claude with optional vision support.

        Args:
            prompt: Text prompt
            image_data: Optional image bytes (JPEG/PNG) for vision models

        Returns:
            Generated narration text
        """
        # If image data is provided and vision is enabled, use vision model
        if image_data and self.use_vision:
            # Encode image to base64
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Determine media type (JPEG or PNG)
            media_type = "image/jpeg"  # Our slides are now JPEG from optimization

            # Create multi-modal message with image
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_base64
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]

            # Use vision-capable model (Claude 3 models support vision)
            model = self.model if "claude-3" in self.model.lower() else "claude-3-5-sonnet-20241022"
        else:
            # Text-only message
            content = prompt
            model = self.model

        response = self.client.messages.create(
            model=model,
            max_tokens=Config.LLM_MAX_TOKENS,
            temperature=Config.LLM_TEMPERATURE,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )
        return response.content[0].text.strip()

    def _generate_anthropic_multimodal(self, prompt: str, images: List[Dict]) -> str:
        """Generate using Anthropic Claude with MULTIPLE images (previous slides + current).

        Args:
            prompt: Text prompt
            images: List of dicts with 'slide_number', 'title', 'image_data', and optional 'is_current'

        Returns:
            Generated narration text
        """
        import base64

        # Build content with all images
        content = []

        # Enhance prompt to mention previous slide images
        enhanced_prompt = prompt
        if len(images) > 1:
            prev_count = sum(1 for img in images if not img.get('is_current', False))
            enhanced_prompt = f"""IMPORTANT: You are seeing {len(images)} slide images:
- {prev_count} previous slide(s) for visual context
- 1 current slide that you're narrating

Use the previous slides' visual elements to create coherent transitions and avoid repeating visual descriptions.

{prompt}"""

        # Add all images with text labels
        for img in images:
            is_current = img.get('is_current', False)
            label = f"[CURRENT SLIDE {img['slide_number']}]" if is_current else f"[Previous Slide {img['slide_number']}: {img['title']}]"

            # Add label
            content.append({
                "type": "text",
                "text": label
            })

            # Add image
            image_base64 = base64.b64encode(img['image_data']).decode('utf-8')
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_base64
                }
            })

        # Add the prompt at the end
        content.append({
            "type": "text",
            "text": enhanced_prompt
        })

        # Use vision-capable model
        model = self.model if "claude-3" in self.model.lower() else "claude-3-5-sonnet-20241022"

        response = self.client.messages.create(
            model=model,
            max_tokens=Config.LLM_MAX_TOKENS,
            temperature=Config.LLM_TEMPERATURE,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )
        return response.content[0].text.strip()

    def _generate_continuous_narration(
        self,
        slides: List[Slide],
        context: Optional[str],
        style: str
    ) -> List[SlideNarration]:
        """Generate a single continuous narration for all slides with vision support."""

        # Check if we should use vision (if any slide has image data)
        use_vision_for_batch = self.use_vision and any(slide.image_data for slide in slides)

        if use_vision_for_batch:
            # With vision: Send ALL images in ONE API call
            print(f"🎨 Vision-enabled continuous mode: Sending all {len(slides)} slides with images in one request")
            return self._generate_continuous_narration_multimodal(slides, context, style)
        else:
            # Without vision: Use text-only batch processing
            print(f"📝 Text-only continuous mode: Processing {len(slides)} slides")
            return self._generate_continuous_narration_text_only(slides, context, style)

    def _generate_continuous_narration_multimodal(
        self,
        slides: List[Slide],
        context: Optional[str],
        style: str
    ) -> List[SlideNarration]:
        """Generate continuous narration by sending ALL slide images in ONE API call.

        This is the most efficient approach - one request with all images instead of N requests.
        """
        import base64

        # Build combined prompt with all slides
        combined_content = "\n\n".join([
            f"SLIDE {slide.slide_number}:\n"
            f"Title: {slide.title}\n"
            f"Content:\n{slide.content}\n"
            + (f"Speaker Notes: {slide.notes}\n" if slide.notes else "")
            for slide in slides
        ])

        prompt = f"""You are generating a spoken narration for a presentation.

Slides:
{combined_content}

{f"Additional Context: {context}" if context else ""}

TASK:
Generate a natural, spoken explanation for the entire presentation in a {style} style.
The narration should:
1. Explain the content of the slides in a cohesive and logical manner.
2. Analyze the visual elements in each slide image provided below.
3. Create smooth transitions between slides, referencing visual elements when appropriate.
4. Be suitable for text-to-speech (avoid special characters, use natural speech).
5. Be concise but complete (aim for 30-90 seconds per slide when spoken).
"""

        # Define function schema for structured output
        narration_function = {
            "name": "generate_narrations",
            "description": "Generate narrations for presentation slides",
            "parameters": {
                "type": "object",
                "properties": {
                    "narrations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "slide_number": {
                                    "type": "integer",
                                    "description": "The slide number"
                                },
                                "narration": {
                                    "type": "string",
                                    "description": "The narration text for this slide"
                                }
                            },
                            "required": ["slide_number", "narration"]
                        }
                    }
                },
                "required": ["narrations"]
            }
        }

        narration_data = []  # Initialize to avoid unbound variable

        # Prepare content with all images
        if self.provider == "openai":
            content = [{"type": "text", "text": prompt}]

            # Add all slide images
            for slide in slides:
                if slide.image_data:
                    content.append({
                        "type": "text",
                        "text": f"\n[SLIDE {slide.slide_number} IMAGE: {slide.title}]"
                    })
                    image_base64 = base64.b64encode(slide.image_data).decode('utf-8')
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "high"
                        }
                    })

            # Make single API call with function calling
            messages = [
                {"role": "system", "content": "You are an expert presenter creating engaging spoken narrations for slides."},
                {"role": "user", "content": content}
            ]

            model = self.model if "vision" in self.model.lower() or "gpt-4" in self.model.lower() else "gpt-4-turbo"

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=Config.LLM_TEMPERATURE,
                max_tokens=Config.LLM_MAX_TOKENS,
                functions=[narration_function],
                function_call={"name": "generate_narrations"}
            )

            # Extract function call response
            import json
            function_response = response.choices[0].message.function_call.arguments
            parsed_response = json.loads(function_response)
            narration_data = parsed_response["narrations"]

        elif self.provider == "anthropic":
            content = []

            # Add all slide images
            for slide in slides:
                if slide.image_data:
                    content.append({
                        "type": "text",
                        "text": f"\n[SLIDE {slide.slide_number} IMAGE: {slide.title}]"
                    })
                    image_base64 = base64.b64encode(slide.image_data).decode('utf-8')
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    })

            # Add prompt at the end (Anthropic doesn't support function calling with vision yet, fallback to JSON)
            json_prompt = prompt + """

Return the narration in the following JSON format:
[
  {"slide_number": 1, "narration": "Narration for slide 1..."},
  {"slide_number": 2, "narration": "Narration for slide 2..."},
  ...
]

Generate ONLY the JSON output, without any additional text or commentary."""

            content.append({"type": "text", "text": json_prompt})

            model = self.model if "claude-3" in self.model.lower() else "claude-3-5-sonnet-20241022"

            response = self.client.messages.create(
                model=model,
                max_tokens=Config.LLM_MAX_TOKENS,
                temperature=Config.LLM_TEMPERATURE,
                messages=[{"role": "user", "content": content}]
            )
            narration_text = response.content[0].text.strip()

            # Parse JSON response for Anthropic
            import json
            try:
                narration_data = json.loads(narration_text)
            except json.JSONDecodeError:
                print("Error: Failed to parse JSON response from Anthropic.")
                print("Raw response:", narration_text)
                raise ValueError("Failed to parse JSON response from Anthropic.")

        # Build narrations list
        narrations = []
        for slide in slides:
            slide_narration = next((item for item in narration_data if item["slide_number"] == slide.slide_number), None)
            narration_segment = slide_narration["narration"] if slide_narration else ""

            if not narration_segment.endswith("."):
                narration_segment += " (truncated)"

            word_count = len(narration_segment.split())
            duration = (word_count / 150) * 60

            narrations.append(SlideNarration(
                slide_number=slide.slide_number,
                narration_text=narration_segment,
                estimated_duration=duration
            ))

        print(f"✅ Generated continuous narration for {len(slides)} slides with {sum(1 for s in slides if s.image_data)} images in ONE request")
        return narrations

    def _generate_continuous_narration_text_only(
        self,
        slides: List[Slide],
        context: Optional[str],
        style: str
    ) -> List[SlideNarration]:
        """Generate continuous narration using text-only batch processing (legacy mode)."""
        # Combine all slides into a single context
        combined_content = "\n\n".join(
            [
                f"SLIDE {slide.slide_number}:\n"
                f"Title: {slide.title}\n"
                f"Content:\n{slide.content}\n"
                + (f"Speaker Notes: {slide.notes}\n" if slide.notes else "")
                for slide in slides
            ]
        )

        # Build a single prompt for all slides
        prompt = f"""You are generating a spoken narration for a presentation.

Slides:
{combined_content}

{f"Additional Context: {context}" if context else ""}

TASK:
Generate a natural, spoken explanation for the entire presentation in a {style} style.
The narration should:
1. Explain the content of the slides in a cohesive and logical manner.
2. Provide clear transitions between topics.
3. Be suitable for text-to-speech (avoid special characters, use natural speech).
4. Be concise but complete (aim for 30-90 seconds per slide when spoken).
"""

        # Define function schema for structured output
        narration_function = {
            "name": "generate_narrations",
            "description": "Generate narrations for presentation slides",
            "parameters": {
                "type": "object",
                "properties": {
                    "narrations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "slide_number": {
                                    "type": "integer",
                                    "description": "The slide number"
                                },
                                "narration": {
                                    "type": "string",
                                    "description": "The narration text for this slide"
                                }
                            },
                            "required": ["slide_number", "narration"]
                        }
                    }
                },
                "required": ["narrations"]
            }
        }

        # Call LLM based on provider with function calling
        narration_data = []
        if self.provider == "openai":
            import json

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert presenter creating engaging spoken narrations for slides."},
                    {"role": "user", "content": prompt}
                ],
                temperature=Config.LLM_TEMPERATURE,
                max_tokens=Config.LLM_MAX_TOKENS,
                functions=[narration_function],
                function_call={"name": "generate_narrations"}
            )

            # Extract function call response
            function_response = response.choices[0].message.function_call.arguments
            parsed_response = json.loads(function_response)
            narration_data = parsed_response["narrations"]

            print("✅ Generated continuous narration using function calling (structured output)")
        else:
            # Fallback for other providers - use JSON parsing
            narration_text = self._generate_openai(prompt + """

Return the narration in the following JSON format:
[
  {"slide_number": 1, "narration": "Narration for slide 1."},
  {"slide_number": 2, "narration": "Narration for slide 2."},
  ...
]

Generate ONLY the JSON output, without any additional text or commentary.""")

            import json
            try:
                narration_data = json.loads(narration_text)
            except json.JSONDecodeError:
                print("Error: Failed to parse JSON response from LLM.")
                print("Raw response:", narration_text)
                raise ValueError("Failed to parse JSON response from LLM.")

        narrations = []
        for slide in slides:
            # Find the corresponding narration for the slide
            slide_narration = next((item for item in narration_data if item["slide_number"] == slide.slide_number), None)
            narration_segment = slide_narration["narration"] if slide_narration else ""

            # Handle potential truncation
            if not narration_segment.endswith("."):
                narration_segment += " (truncated)"

            # Estimate duration (150 words per minute)
            word_count = len(narration_segment.split())
            duration = (word_count / 150) * 60

            narrations.append(SlideNarration(
                slide_number=slide.slide_number,
                narration_text=narration_segment,
                estimated_duration=duration
            ))

        return narrations
