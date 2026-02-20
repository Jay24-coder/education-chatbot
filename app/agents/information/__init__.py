"""Information agents: Syllabus, Administration, Topic Expert."""

from app.agents.information.administration_agent import AdministrationAgent
from app.agents.information.syllabus_agent import SyllabusAgent
from app.agents.information.topic_expert_agent import TopicExpertAgent

__all__ = ["SyllabusAgent", "AdministrationAgent", "TopicExpertAgent"]
