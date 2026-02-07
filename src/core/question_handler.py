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
        additional_context: Optional[str] = None
    ) -> str:
        """
        Answer a user question in context of the current slide.
        
        Args:
            question: User's question
            current_slide: The slide being viewed
            current_narration: The narration for current slide
            all_slides: All slides in presentation
            additional_context: Any additional context (notes, documents)
            
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
            additional_context
        )
        
        # Get answer from LLM
        answer = self._answer_openai(prompt)
        
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
        additional_context: Optional[str]
    ) -> str:
        """Build prompt for answering question."""
        
        # Get context from previous and next slides
        prev_slide = all_slides[current_slide.slide_number - 2] if current_slide.slide_number > 1 else None
        next_slide = all_slides[current_slide.slide_number] if current_slide.slide_number < len(all_slides) else None
        
        prompt = f"""You are an AI assistant helping a user during a presentation. The user is viewing a specific slide and has asked a question.

CURRENT SLIDE (Slide {current_slide.slide_number}):
Title: {current_slide.title}
Content: {current_slide.content}
Narration: {current_narration.narration_text}

{f"PREVIOUS SLIDE: {prev_slide.title}" if prev_slide else ""}
{f"NEXT SLIDE: {next_slide.title}" if next_slide else ""}

{f"ADDITIONAL CONTEXT: {additional_context}" if additional_context else ""}

CONVERSATION HISTORY:
{self._format_conversation_history()}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer the question clearly and concisely
2. Reference the current slide content when relevant
3. Keep answers focused and suitable for spoken delivery
4. If you don't know or it's not in the context, say so honestly

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
    
    def _answer_openai(self, prompt: str) -> str:
        """Answer using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful presentation assistant that answers questions about slide content."},
                {"role": "user", "content": prompt}
            ],
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
