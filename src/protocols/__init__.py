from src.protocols.round_robin import execute as round_robin
from src.protocols.point_counterpoint import execute as point_counterpoint
from src.protocols.cross_examination import execute as cross_examination

EXECUTORS = {'round_robin': round_robin, 'point_counterpoint': point_counterpoint,
             'cross_examination': cross_examination}
