# pylint: disable=invalid-name
import decimal
import json
from datetime import date, datetime
from pathlib import Path, PosixPath
from uuid import UUID


class CamundaJSONEncoder(json.JSONEncoder):
    @staticmethod
    def time_format(dt):
        # pylint: disable=invalid-name
        return f"{dt.strftime('%Y-%m-%dT%H:%M')}:{(dt.second + dt.microsecond / 1e6):.3f}{dt.strftime('%z')}"

    def default(self, o):

        # convert UUID to str
        if isinstance(o, UUID):
            return str(o)

        # convert Path to str
        if isinstance(o, (Path, PosixPath)):
            return o.as_posix()

        # handle decimal values
        if isinstance(o, decimal.Decimal):
            return float(o)

        # handle date values
        if isinstance(o, date):
            return o.isoformat()

        # handle datetime values
        if isinstance(o, datetime):
            return self.time_format(o)

        return super().default(o)
