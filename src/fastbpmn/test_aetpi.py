import asyncio
import logging

from fastbpmn.aetpi.logonly import LogOnlyExternalTaskProcessor
from fastbpmn.aetpi.servers.camunda7.server import Camunda7Server


async def main():
    queue = asyncio.Queue()

    for i in range(0, 10):
        await queue.put(
            {
                "type": "externaltask",
                "protocol": "camunda7",
                "aetpi": {"version": "1.0", "spec_version": "1.0"},
                "task": {
                    "id": "12345678-1234-5678-1234-567812345678",
                    "topic": f"topic+{i}",
                },
            }
        )

    application = LogOnlyExternalTaskProcessor()

    server = Camunda7Server(
        name="test", queue=queue, process_engine=None, app=application
    )
    await server()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    print("Done.")
