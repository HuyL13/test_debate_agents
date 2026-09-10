from src.legacy_protocols.round_robin import execute as round_robin
from src.legacy_protocols.point_counterpoint import execute as point_counterpoint
from src.legacy_protocols.cross_examination import execute as cross_examination

EXECUTORS = {'round_robin': round_robin, 'point_counterpoint': point_counterpoint,
             'cross_examination': cross_examination}
