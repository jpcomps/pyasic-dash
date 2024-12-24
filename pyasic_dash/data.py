import numpy as np
from pyasic.data import AlgoHashRateType, MinerData
from pyasic.device.algorithm.hashrate.base import GenericHashrate
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer


class MinerTableData(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    location: str
    ip: str
    status: bool = False
    model: str = "Unknown"
    make: str = "Unknown"
    firmware: str | None = Field(serialization_alias="fw", default=None)
    temperature: int | None = Field(serialization_alias="temp", default=None)
    hashrate: AlgoHashRateType | None = None
    performance: int | None = Field(serialization_alias="perf", default=None)
    real_power: int | None = Field(serialization_alias="rpower", default=None)
    efficiency: int | None = Field(serialization_alias="eff", default=None)
    hostname: str | None = None
    worker: str | None = None
    voltage: float | None = None
    hashboard_count: int = Field(serialization_alias="hbs", default=0)
    hashboard_1: AlgoHashRateType | None = Field(
        serialization_alias="hb0", default=None
    )
    hashboard_2: AlgoHashRateType | None = Field(
        serialization_alias="hb1", default=None
    )
    hashboard_3: AlgoHashRateType | None = Field(
        serialization_alias="hb2", default=None
    )
    hashboard_4: AlgoHashRateType | None = Field(
        serialization_alias="hb3", default=None
    )

    @field_serializer("hashrate")
    def serialize_hashrate(self, value: AlgoHashRateType | None) -> float | None:
        if value is not None:
            return round(float(value), 2)
        return None

    @field_serializer("hashboard_1")
    def serialize_hashboard_1(self, value: AlgoHashRateType | None) -> float | None:
        if value is not None:
            return round(float(value), 2)
        return None

    @field_serializer("hashboard_2")
    def serialize_hashboard_2(self, value: AlgoHashRateType | None) -> float | None:
        if value is not None:
            return round(float(value), 2)
        return None

    @field_serializer("hashboard_3")
    def serialize_hashboard_3(self, value: AlgoHashRateType | None) -> float | None:
        if value is not None:
            return round(float(value), 2)
        return None

    @field_serializer("hashboard_4")
    def serialize_hashboard_4(self, value: AlgoHashRateType | None) -> float | None:
        if value is not None:
            return round(float(value), 2)
        return None

    @classmethod
    def from_miner_data(cls, m_data: MinerData, location: str):
        active_pools = [pool.user for pool in m_data.pools if pool.active]
        hbs = {f"hashboard_{n}": None for n in range(4)}
        hbs.update(**{f"hashboard_{b.slot + 1}": b.hashrate for b in m_data.hashboards})
        hb_voltages = [b.voltage for b in m_data.hashboards if b.voltage is not None]
        return cls(
            location=location,
            ip=m_data.ip,
            status=m_data.is_mining and float(m_data.hashrate) > 0,
            model=m_data.model,
            make=m_data.make,
            firmware=m_data.firmware,
            temperature=m_data.temperature_avg,
            hashrate=m_data.hashrate,
            performance=m_data.percent_expected_hashrate,
            real_power=m_data.wattage,
            efficiency=m_data.efficiency,
            hostname=m_data.hostname,
            worker=active_pools[0] if len(active_pools) > 0 else None,
            hashboard_count=len(
                [
                    b
                    for b in m_data.hashboards
                    if not b.missing and float(b.hashrate) > 0
                ]
            ),
            **hbs,
            voltage=np.max(hb_voltages) if len(hb_voltages) > 0 else None,
        )


class MinerFullTableData(BaseModel):
    data: list[MinerTableData] = Field(default_factory=list)

    @computed_field  # type: ignore[misc]
    @property
    def total_hashrate(self) -> GenericHashrate:
        return sum(
            [d.hashrate for d in self.data if d.hashrate is not None],
            start=GenericHashrate(),
        )
