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
        style: str = "educational"
    ) -> List[SlideNarration]:
        """
        Generate narration for all slides.
        
        Args:
            slides: List of parsed slides
            context: Additional context (lecture notes, documents)
            style: Narration style (educational, professional, casual)
            
        Returns:
            List of SlideNarration objects
        """
        narrations = []
        
        for slide in slides:
            narration_text = self._generate_single_narration(
                slide, 
                context=context,
                style=style,
                previous_slides=slides[:slide.slide_number-1]
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
        previous_slides: List[Slide]
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
        previous_slides: List[Slide]
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
1. Explain what the slide shows
2. Provide context and reasoning
3. Be suitable for text-to-speech (avoid special characters, use natural speech)
4. Flow naturally from previous slides
5. Be concise but complete (aim for 30-90 seconds when spoken)

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
