from typing import List

from pydantic import BaseModel


class TimeseriesPoint(BaseModel):
    label: str       # e.g. "Mon", "Week 1", "Jan"
    value: float


class CallVolumeOut(BaseModel):
    range: str
    points: List[TimeseriesPoint]


class LanguageBreakdownOut(BaseModel):
    language: str
    count: int
    percent: float


class SentimentTrendOut(BaseModel):
    range: str
    positive: List[TimeseriesPoint]
    neutral: List[TimeseriesPoint]
    negative: List[TimeseriesPoint]


class PerformanceOut(BaseModel):
    avg_latency_ms: float
    avg_duration_seconds: float
    total_calls: int
    resolution_rate: float