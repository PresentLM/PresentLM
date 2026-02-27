"""
Question Handler - Answers user questions during presentation using LLM.
Maintains context of the current slide and presentation flow.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
import openai

from ..utils.config import Config
from ..utils.benchmark import get_benchmark_tracker
from .slide_parser import Slide
from .narration_generator import SlideNarration


@dataclass
class QuestionAnswer:
    """Represents a question and its answer."""
    question: str
    answer: str
    slide_number: int
    timestamp: float


class QuestionHandler:
    """Handle user questions during presentation."""
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize question handler.
        
        Args:
            provider: LLM provider (always uses openai)
            model: Model name
        """
        self.provider = "openai"
        self.model = model or Config.LLM_MODEL
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.conversation_history: List[QuestionAnswer] = []
    
    def answer_question(
        self,
        question: str,
        current_slide: Slide,
        current_narration: SlideNarration,
        all_slides: List[Slide],
        additional_context: Optional[str] = None,
        use_vision: bool = True
    ) -> str:
        """
        Answer a user question in context of the current slide.
        
        Args:
            question: User's question
            current_slide: The slide being viewed
            current_narration: The narration for current slide
            all_slides: All slides in presentation
            additional_context: Any additional context (notes, documents)
            use_vision: Whether to include slide image in the prompt (default: True)

        Returns:
            Answer text
        """
        # Start benchmarking
        benchmark = get_benchmark_tracker()
        timer_id = f"answer_question_{id(self)}"
        benchmark.start_timer(timer_id)
        
        # Build context-aware prompt
        prompt = self._build_question_prompt(
            question,
            current_slide,
            current_narration,
            all_slides,
            additional_context,
            use_vision
        )
        
        # Get answer from LLM (with optional image)
        image_data = current_slide.image_data_compressed if (use_vision and current_slide.image_data_compressed) else None

        # Log vision usage
        if image_data:
            print(f"🎨 Question answering: Using vision for slide {current_slide.slide_number} ({len(image_data)/1024:.1f} KB image)")

        answer = self._answer_openai(prompt, image_data=image_data)

        # End benchmarking
        duration = benchmark.end_timer(
            timer_id,
            component="QuestionHandler",
            operation="answer_question",
            metadata={
                "provider": self.provider,
                "model": self.model,
                "question_length": len(question),
                "answer_length": len(answer),
                "slide_number": current_slide.slide_number,
                "conversation_history_length": len(self.conversation_history)
            }
        )
        
        print(f"[BENCHMARK] QuestionHandler.answer_question: {duration:.2f}s (Q:{len(question)} chars, A:{len(answer)} chars)")
        
        # Store in conversation history
        qa = QuestionAnswer(
            question=question,
            answer=answer,
            slide_number=current_slide.slide_number,
            timestamp=0.0  # Will be set by caller
        )
        self.conversation_history.append(qa)
        
        return answer
    
    def _build_question_prompt(
        self,
        question: str,
        current_slide: Slide,
        current_narration: SlideNarration,
        all_slides: List[Slide],
        additional_context: Optional[str],
        use_vision: bool
    ) -> str:
        """Build prompt for answering question."""
        
        # Get context from previous and next slides
        prev_slide = all_slides[current_slide.slide_number - 2] if current_slide.slide_number > 1 else None
        next_slide = all_slides[current_slide.slide_number] if current_slide.slide_number < len(all_slides) else None
        
        # Add vision-specific instructions if image is present
        vision_instruction = ""
        if use_vision and current_slide.image_data:
            vision_instruction = """
The slide image is provided. Please analyze:
- Visual elements (diagrams, charts, images, graphics)
- Layout and design elements that convey meaning
- Text visible in the image that may not be captured in the content above
- Colors, icons, or visual metaphors that enhance understanding

Use the visual information to provide more accurate and complete answers.
"""

        prompt = f"""You are an AI assistant helping a user during a presentation. The user is viewing a specific slide and has asked a question.

CURRENT SLIDE (Slide {current_slide.slide_number}):
Title: {current_slide.title}
Content: {current_slide.content}
Narration: {current_narration.narration_text}

{f"PREVIOUS SLIDE: {prev_slide.title}" if prev_slide else ""}
{f"NEXT SLIDE: {next_slide.title}" if next_slide else ""}

{f"ADDITIONAL CONTEXT: {additional_context}" if additional_context else ""}

{vision_instruction}

CONVERSATION HISTORY:
{self._format_conversation_history()}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer the question clearly and concisely
2. Reference the current slide content when relevant
3. Keep answers focused and suitable for spoken delivery
4. If you don't know or it's not in the context, say so honestly
{f"5. Use visual information from the slide image to enhance your answer" if use_vision and current_slide.image_data else ""}

Provide ONLY the answer, without any meta-commentary."""
        
        return prompt
    
    def _format_conversation_history(self) -> str:
        """Format recent conversation history."""
        if not self.conversation_history:
            return "No previous questions."
        
        recent = self.conversation_history[-3:]  # Last 3 Q&A pairs
        formatted = []
        for qa in recent:
            formatted.append(f"Q: {qa.question}\nA: {qa.answer}")
        
        return "\n\n".join(formatted)
    
    def _answer_openai(self, prompt: str, image_data: Optional[bytes] = None) -> str:
        """Answer using OpenAI with optional vision support.

        Args:
            prompt: Text prompt
            image_data: Optional image bytes (JPEG/PNG) for vision models

        Returns:
            Generated answer text
        """
        messages = [
            {"role": "system", "content": "You are a helpful presentation assistant that answers questions about slide content."}
        ]

        # If image data is provided, use vision model
        if image_data:
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
                            "detail": "high"  # high detail for better analysis
                        }
                    }
                ]
            })

            # Use vision-capable model
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
            temperature=0.7,
            max_tokens=500  # Shorter answers for questions
        )
        return response.choices[0].message.content.strip()
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def get_history(self) -> List[QuestionAnswer]:
        """Get conversation history."""
        return self.conversation_history
