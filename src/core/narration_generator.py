"""
Narration Generator - Creates structured spoken explanations for slides using LLM.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import openai

from ..utils.config import Config
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


class NarrationGenerator:
    """Generate narration for slides using LLM."""
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize narration generator.
        
        Args:
            provider: LLM provider (openai, anthropic, google). Defaults to Config.
            model: Model name. Defaults to Config.
        """
        self.provider = provider or Config.LLM_PROVIDER
        self.model = model or Config.LLM_MODEL
        
        # Initialize client based on provider
        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
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
        if mode == "continuous":
            return self._generate_continuous_narration(slides, context, style)

        narrations = []
        for slide in slides:
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

        return narrations

    def _generate_single_narration(
        self,
        slide: Slide,
        context: Optional[str],
        style: str,
        previous_slides: List[Slide],
    ) -> str:
        """Generate narration for a single slide."""

        # Build prompt
        prompt = self._build_prompt(slide, context, style, previous_slides)

        # Call LLM based on provider
        if self.provider == "openai":
            return self._generate_openai(prompt)

    def _build_prompt(
        self,
        slide: Slide,
        context: Optional[str],
        style: str,
        previous_slides: List[Slide],
    ) -> str:
        """Build the prompt for narration generation."""

        prompt = f"""You are generating a spoken narration for a presentation slide.

SLIDE {slide.slide_number}:
Title: {slide.title}
Content:
{slide.content}

{f"Speaker Notes: {slide.notes}" if slide.notes else ""}

{f"Additional Context: {context}" if context else ""}

TASK:
Generate a natural, spoken explanation for this slide in a {style} style.
The narration should:
1. Explain what the slide shows and how it connects to the previous slide if relevant.
2. Avoid repeating information already covered in previous slides.
3. Provide new insights or details that build on the previous slides.
4. Be suitable for text-to-speech (avoid special characters, use natural speech).
5. Flow naturally from previous slides with clear transitions.
6. Be concise but complete (aim for 30-90 seconds when spoken).

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

    def _generate_openai(self, prompt: str) -> str:
        """Generate using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert presenter creating engaging spoken narrations for slides."},
                {"role": "user", "content": prompt}
            ],
            temperature=Config.LLM_TEMPERATURE,
            max_tokens=Config.LLM_MAX_TOKENS
        )
        return response.choices[0].message.content.strip()

    def _generate_continuous_narration(
        self,
        slides: List[Slide],
        context: Optional[str],
        style: str
    ) -> List[SlideNarration]:
        """Generate a single continuous narration for all slides."""
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

Return the narration in the following JSON format:
[
  {{"slide_number": 1, "narration": "Narration for slide 1."}},
  {{"slide_number": 2, "narration": "Narration for slide 2."}},
  ...
]

Generate ONLY the JSON output, without any additional text or commentary.
"""

        # Call LLM based on provider
        narration_text = ""  # Initialize narration_text to avoid unbound variable error
        if self.provider == "openai":
            narration_text = self._generate_openai(prompt)

        # Debugging: Log the raw response from the LLM
        print("Raw LLM Response:", narration_text)

        # Parse the JSON response from the LLM
        import json
        try:
            narration_data = json.loads(narration_text)
        except json.JSONDecodeError:
            # Log the error and provide a fallback
            print("Error: Failed to parse JSON response from LLM.")
            print("Raw response was:", narration_text)
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
