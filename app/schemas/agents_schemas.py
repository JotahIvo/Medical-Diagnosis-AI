from typing import List, Optional, Union
from pydantic import BaseModel, Field


class SymptomInput(BaseModel):
    symptoms: str = Field(..., description="Description of the patient's symptoms.")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity.")
    user_id: Optional[str] = Field(None, description="User id.")


class DiagnosisHypothesis(BaseModel):
    diagnosis: str = Field(..., description="Name of the hypothetical medical condition.")
    confidence: str = Field(..., description="Level of confidence in the hypothesis.")
    justification: str = Field(..., description="Brief justification based on symptoms.")
    severity: str = Field(..., description="Estimated severity of the condition.")


class ExamRecommendation(BaseModel):
    name: str = Field(..., description="Name of the recommended exam.")
    justification: str = Field(..., description="Justification for the exam.")


class TreatmentSuggestion(BaseModel):
    name: str = Field(..., description="Name of the suggested treatment.")
    justification: str = Field(..., description="Justification for the treatment.")


class ClinicalAction(BaseModel):
    condition: Optional[str] = Field(None, description="Medical condition of the original hypothesis.")
    severity: Optional[str] = Field(None, description="Severity of condition.")
    exam_recommendations: List[Union[ExamRecommendation, str]] = Field(default_factory=list, description="List of recommended exams.")
    treatment_suggestions: List[Union[TreatmentSuggestion, str]] = Field(default_factory=list, description="Treatment or management suggestions.")
    urgency: str = Field(..., description="Level of urgency of action.")
    justification: Optional[str] = Field(None, description="Justification for suggested tests/treatments.")


class MedicalDiagnosisResponse(BaseModel):
    diagnosis: DiagnosisHypothesis = Field(..., description="Diagnostic hypothesis.")
    action_plan: ClinicalAction = Field(..., description="Suggested action plan.")
    rag_sources: List[str] = Field(default_factory=list, description="Sources consulted in RAG.")
    notes: str = Field(..., description="Additional notes or general recommendations for the patient.")


class ClinicalProtocolInput(BaseModel):
    session_id: str = Field(..., description="Session ID for conversation continuity.")
    diagnosis: DiagnosisHypothesis = Field(..., description="The diagnostic hypothesis from the first agent.")
    