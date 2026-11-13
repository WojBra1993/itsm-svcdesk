# ai-generated: 100% - Codex wrote behavioural boundary tests from the course module's documented contract.
from datetime import datetime, timedelta
import pytest
import slaclock as s


@pytest.mark.parametrize('vip,expected', [(False, ['P1','P2','P3','P2','P3','P4','P3','P4','P4']), (True, ['P1','P2','P2','P2','P2','P2','P2','P2','P2'])])
def test_matrix(vip, expected):
    assert [s.priority_of(i, u, vip) for i in (1,2,3) for u in (1,2,3)] == expected


@pytest.mark.parametrize('bad', [-1, 0, 4, 2.0, True, False, '1', None])
def test_priority_validation(bad):
    with pytest.raises(ValueError):
        s.priority_of(bad, 2)
    with pytest.raises(ValueError):
        s.priority_of(2, bad, True)


@pytest.mark.parametrize('priority,expected', [('P1',(15,240)),('P2',(60,480)),('P3',(240,1440)),('P4',(480,4320))])
def test_targets(priority, expected):
    assert s.targets(priority) == expected


@pytest.mark.parametrize('priority', ['p1',' P1','P1 ','P0','P5',''])
def test_invalid_priority(priority):
    with pytest.raises(ValueError):
        s.targets(priority)
    with pytest.raises(ValueError):
        s.escalation_tier(priority, False, 0)


@pytest.mark.parametrize('elapsed,target,expected', [(0,1,'ok'),(1,1,'warning'),(2,1,'breached'),(74,100,'ok'),(75,100,'warning'),(76,100,'warning'),(100,100,'warning'),(101,100,'breached'),(11,15,'ok'),(12,15,'warning'),(15,15,'warning'),(16,15,'breached')])
def test_thresholds(elapsed,target,expected):
    assert s.sla_state(elapsed,target) == expected


@pytest.mark.parametrize('elapsed,target', [(-1,100),(0,0),(1,-1)])
def test_invalid_clock(elapsed,target):
    with pytest.raises(ValueError):
        s.sla_state(elapsed,target)


@pytest.mark.parametrize('day', range(7))
@pytest.mark.parametrize('hour,minute,inside', [(7,59,False),(8,0,True),(12,0,True),(15,59,True),(16,0,False),(23,59,False)])
def test_business_window(day,hour,minute,inside):
    value = datetime(2026,11,9,hour,minute,59,999999) + timedelta(days=day)
    assert s.is_business_time(value) is (inside and day < 5)


@pytest.mark.parametrize('start,minutes,end', [
    ('2026-11-13T15:59:59',1,'2026-11-13T16:00'),
    ('2026-11-13T15:59',2,'2026-11-16T08:01'),
    ('2026-11-13T16:00',0,'2026-11-16T08:00'),
    ('2026-11-14T12:00',0,'2026-11-16T08:00'),
    ('2026-11-15T12:00',1,'2026-11-16T08:01'),
    ('2026-11-09T07:59',0,'2026-11-09T08:00'),
    ('2026-11-09T08:00:59',0,'2026-11-09T08:00'),
    ('2026-11-09T08:00',480,'2026-11-09T16:00'),
    ('2026-11-09T08:00',481,'2026-11-10T08:01'),
    ('2026-11-09T12:30',210,'2026-11-09T16:00'),
    ('2026-11-09T12:30',211,'2026-11-10T08:01'),
    ('2026-11-09T08:00',2400,'2026-11-13T16:00'),
    ('2026-11-09T08:00',2401,'2026-11-16T08:01'),
])
def test_due_dates(start,minutes,end):
    start,end = datetime.fromisoformat(start),datetime.fromisoformat(end)
    assert s.add_business_minutes(start,minutes) == end
    assert s.business_minutes_between(start,end) == minutes


@pytest.mark.parametrize('start,end,expected', [
    ('2026-11-09T07:00','2026-11-09T07:59',0),
    ('2026-11-09T16:00','2026-11-09T20:00',0),
    ('2026-11-14T00:00','2026-11-15T23:59',0),
    ('2026-11-09T12:30','2026-11-10T09:00',270),
    ('2026-11-13T15:30','2026-11-16T08:30',60),
    ('2026-11-09T12:00:59','2026-11-09T12:00:00',0),
    ('2026-11-09T12:00:59','2026-11-09T12:01:00',1),
])
def test_elapsed(start,end,expected):
    assert s.business_minutes_between(datetime.fromisoformat(start),datetime.fromisoformat(end)) == expected


def test_span_limits():
    start = datetime(2026,11,9,8)
    end = start + timedelta(days=366)
    # Independent calendar count; business dates in [start date, end date).
    expected = sum(480 for i in range(366) if (start + timedelta(days=i)).weekday() < 5)
    assert s.business_minutes_between(start,end) == expected
    assert s.add_business_minutes(start,expected+1) == end + timedelta(minutes=1)
    with pytest.raises(ValueError):
        s.business_minutes_between(start,end+timedelta(days=1))
    with pytest.raises(ValueError):
        s.add_business_minutes(start,expected+481)
    with pytest.raises(ValueError):
        s.add_business_minutes(start,-1)
    with pytest.raises(ValueError):
        s.business_minutes_between(start,start-timedelta(minutes=1))


@pytest.mark.parametrize('priority,normal,breached', [('P1',1,3),('P2',1,2),('P3',0,1),('P4',0,1)])
def test_escalation(priority,normal,breached):
    for reopens,increment in [(0,0),(1,0),(2,1),(3,1),(100,1)]:
        assert s.escalation_tier(priority,False,reopens) == min(3,normal+increment)
        assert s.escalation_tier(priority,True,reopens) == min(3,breached+increment)
    with pytest.raises(ValueError):
        s.escalation_tier(priority,False,-1)


@pytest.mark.parametrize('text,expected', [('1m',1),('90m',90),('4h',240),('1h30m',90),('2d',2880),('1d4h',1680),('1d0h5m',1445),('1h59m',119),('60m',60),('0h60m',60),('0d0h60m',60),('  1d2h3m\n',1563),('25h',1500)])
def test_duration(text,expected):
    assert s.parse_duration(text) == expected


@pytest.mark.parametrize('text', ['', ' ', '0m','0d0h0m','1.5h','30m1h','-5m','1 h','1H','1h60m','1d60m','1m1m','1h 2m','abc','1hX','X1h'])
def test_bad_duration(text):
    with pytest.raises(ValueError):
        s.parse_duration(text)
