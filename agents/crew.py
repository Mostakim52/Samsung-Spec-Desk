import os
from typing import Optional

from dotenv import load_dotenv
from crewai import Agent, Crew, Task
from crewai.tools import BaseTool

from database import db
from scraper.models import PhoneRecord

load_dotenv()


class PhoneSpecTool(BaseTool):
    name: str = "phone_spec_tool"
    description: str = (
        "Returns the full technical specification sheet for a Samsung phone by name. "
        "Input: exact or partial phone name, e.g. 'Galaxy S23'."
    )

    def _run(self, phone_name: str) -> str:
        record = _get_record(phone_name)
        if record is None:
            return f"Phone '{phone_name}' not found in the catalog."
        return record.to_doc()


def _get_record(phone_name: str) -> Optional[PhoneRecord]:
    record = db.get_phone_by_name(phone_name.strip())
    if record is None:
        from scraper.gsmarena import load_fallback_dataset

        for candidate in load_fallback_dataset():
            if phone_name.strip().lower() in candidate.name.lower():
                record = candidate
                break
    return record


def _llm():
    key = os.getenv("GROQ_API_KEY", "")
    if not key or key == "your_groq_api_key_here":
        return None
    import crewai.llms.cache as _cache
    from crewai import LLM

    _cache.mark_cache_breakpoint = lambda message: dict(message)
    return LLM(
        model="groq/qwen/qwen3.8-27b",
        api_key=key,
        max_tokens=400,
        max_retries=2,
        temperature=0.2,
    )


def generate_review(phone_name: str) -> dict:
    record = _get_record(phone_name)
    if record is None:
        raise LookupError(f"Phone '{phone_name}' not found in the catalog.")
    llm = _llm()
    retriever = Agent(
        role="Spec Retriever",
        goal="Fetch and return the exact technical specifications of the requested phone.",
        backstory="A meticulous phone database curator who never guesses numbers.",
        tools=[PhoneSpecTool()],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    writer = Agent(
        role="Review Writer",
        goal="Write a detailed product review grounded only in the retrieved specs.",
        backstory="A veteran phone reviewer who only writes what the datasheet supports.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    fetch_task = Task(
        description=f"Retrieve the specification sheet for the phone named '{phone_name}' "
        "using the phone_spec_tool. Return the full spec sheet verbatim.",
        expected_output="The complete specification sheet text.",
        agent=retriever,
    )
    review_task = Task(
        description=(
            "Using the retrieved specification sheet, write a concise product review of the "
            f"'{phone_name}' with sections: Overview, Display, Performance, Cameras, Battery, "
            "Verdict. Keep each section to 1-3 sentences. Use only facts from the spec sheet; "
            "do not invent numbers."
        ),
        expected_output="A concise multi-section product review in markdown.",
        agent=writer,
    )
    crew = Crew(agents=[retriever, writer], tasks=[fetch_task, review_task], verbose=False)
    if llm:
        result = crew.kickoff()
        review = str(result)
    else:
        review = _template_review(record)
    return {"review": review, "specs_used": record.raw_specs, "phone": record.name}


def _template_review(record: PhoneRecord) -> str:
    return (
        f"## {record.name} Review\n\n"
        f"**Display** — {record.display_type}, {record.display_size} "
        f"({record.resolution}, {record.refresh_rate})\n\n"
        f"**Performance** — {record.processor}, {record.ram} RAM, {record.storage} "
        "storage\n\n"
        f"**Cameras** — Rear: {record.rear_camera}. Front: {record.front_camera}\n\n"
        f"**Battery** — {record.battery_capacity} ({record.battery_life})\n\n"
        f"**Verdict** — The {record.name} runs {record.os} and launched at "
        f"{record.price}. Set GROQ_API_KEY for the full agent-written review."
    )
