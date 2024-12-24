import asyncio
import logging
from datetime import datetime

import pyasic
from nicegui import events, ui

from pyasic_dash.data import MinerFullTableData, MinerTableData
from pyasic_dash.settings import Location, config

LOGGER = logging.getLogger(__name__)


class MinerTableSection:
    def __init__(self):
        self.refresh_timer = ui.timer(config.interval * 60, self.update)
        self.updating = False
        self.dialog = ui.dialog().props("fullWidth").props("fullHeight")
        self.data: MinerFullTableData = MinerFullTableData()

        with ui.row().classes("w-full justify-between"):
            with ui.column():
                with ui.row():
                    ui.button("Update", on_click=self.update).classes("h-auto mt-auto")
                    ui.button(
                        "Stop Auto Refresh", on_click=self.refresh_timer.cancel
                    ).classes("h-auto mt-auto")
                    ui.number(
                        label="Interval (mins)",
                        value=config.interval,
                        on_change=self.update_refresh_interval,
                    ).classes("h-auto")
            with ui.column().classes("pe-2 mt-auto"):
                with ui.row():
                    ui.label("Last Update:").classes("text-xl mt-auto")
                    self.updating_spinner = ui.spinner("dots", size="lg").classes(
                        "mx-3 mb-0 pt-2"
                    )
                    self.last_update = ui.label().classes("text-xl")
                    self.last_update.bind_text_to(
                        self.updating_spinner, "visible", forward=lambda x: x == ""
                    )

        self.table = (
            ui.aggrid(
                {
                    "defaultColDef": {"flex": 1},
                    "columnDefs": [
                        {
                            "headerName": "Location",
                            "field": "location",
                            "filter": "agTextColumnFilter",
                            "floatingFilter": True,
                        },
                        {
                            "headerName": "IP",
                            "field": "ip",
                            "filter": "agTextColumnFilter",
                            "floatingFilter": True,
                        },
                        {
                            "headerName": "Make",
                            "field": "make",
                            "filter": "agTextColumnFilter",
                            "floatingFilter": True,
                        },
                        {
                            "headerName": "Model",
                            "field": "model",
                            "filter": "agTextColumnFilter",
                            "floatingFilter": True,
                        },
                        {
                            "headerName": "FW",
                            "field": "fw",
                            "filter": "agTextColumnFilter",
                            "floatingFilter": True,
                        },
                        {
                            "headerName": "Hostname",
                            "field": "hostname",
                            "filter": "agTextColumnFilter",
                            "floatingFilter": True,
                        },
                        {"headerName": "Temp", "field": "temp"},
                        {"headerName": "Hashrate", "field": "hashrate"},
                        {
                            "headerName": "Performance",
                            "field": "perf",
                            "cellClassRules": {
                                "bg-red-700": "x < 90 & x != None",
                                "bg-orange-600": "x >= 90 & x < 98",
                                "bg-green-700": "x >= 98",
                            },
                        },
                        {"headerName": "HBs", "field": "hbs", "cellClassRules": {}},
                        {"headerName": "HB0", "field": "hb0", "cellClassRules": {}},
                        {"headerName": "HB1", "field": "hb1", "cellClassRules": {}},
                        {"headerName": "HB2", "field": "hb2", "cellClassRules": {}},
                        {"headerName": "HB3", "field": "hb3", "cellClassRules": {}},
                        {"headerName": "Voltage", "field": "voltage"},
                        {"headerName": "API Power", "field": "rpower"},
                        {"headerName": "Efficiency", "field": "eff"},
                        {
                            "headerName": "Worker",
                            "field": "worker",
                            "filter": "agTextColumnFilter",
                            "floatingFilter": True,
                        },
                        {"headerName": "Status", "field": "status", "hide": True},
                    ],
                    "rowData": [],
                    "rowSelection": "multiple",
                    ":pagination": True,
                },
                theme="balham-dark",
            )
            .style("height: 800px")
            .on(
                "cellClicked",
                lambda e: self.open_dialog(e.args) if e.args["colId"] == "ip" else None,
            )
        )

    async def update(self):
        if len(config.locations) == 0:
            LOGGER.info("No locations defined, not updating table.")
            return
        if self.updating:
            LOGGER.info("Already updating miner table data, skipping re-run.")
            ui.notify("Already Updating", type="negative", position="top")
            return
        try:
            self.last_update.set_text("")
            LOGGER.info("Updating miner data.")
            ui.notify("Updating Data", type="warning", position="top")
            self.updating = True
            self.data = await get_miners_data()
            self.last_update.set_text(f"{datetime.now():%X}")
            LOGGER.info(
                f"Finished updating miner data, found {len(self.data.data)} miners."
            )
            LOGGER.debug(f"Found miner data: {self.data}")
            ui.notify("Updating Data Complete!", type="positive", position="top")
            self.updating = False
            self.table.options["rowData"] = self.data.model_dump(by_alias=True)["data"]
            self.table.update()
        except Exception:
            ui.notify("Failed Update, check logs!", type="negative", position="top")
            self.updating = False
            self.table.options["rowData"] = []
            self.table.update()
            raise

    def handle_theme_change(self, e: events.ValueChangeEventArguments):
        self.table.classes(
            add=f"ag-theme-balham{'-dark' if e.value else ''}",
            remove=f"ag-theme-balham{'' if e.value else '-dark'}",
        )

    def update_refresh_interval(self, e: events.ValueChangeEventArguments):
        self.refresh_timer.interval = e.value * 60

    def open_dialog(self, args):
        ip = args["value"]
        self.dialog.clear()
        with self.dialog, ui.card():
            with ui.row().classes("w-full justify-between"):
                with ui.column():
                    ui.label(f"IP: {ip}").classes("text-xl")
                with ui.column():
                    ui.button(
                        "Close", icon="close", on_click=self.dialog.close
                    ).classes("ml-auto")
            ui.html(
                f'<iframe src="http://{ip}" style="width:100%; height:100%" title="{ip}"></iframe>'
            ).style("margin: 0 auto; width: 100%; height: 100%")
        self.dialog.open()


async def get_miners_data() -> MinerFullTableData:
    data = []
    locations_data = await asyncio.gather(
        *[get_location_miners_data(location) for location in config.locations]
    )
    for location_data in locations_data:
        data.extend(location_data)
    return MinerFullTableData(data=data)


async def get_location_miners_data(location: Location) -> list[MinerTableData]:
    miners = await pyasic.MinerNetwork.from_subnet(location.subnet).scan()
    data = await asyncio.gather(*[m.get_data() for m in miners])
    return [
        MinerTableData.from_miner_data(m_data=d, location=location.name) for d in data
    ]
