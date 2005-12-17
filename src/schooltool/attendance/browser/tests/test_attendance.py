#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Tests for SchoolTool attendance views

$Id$
"""
import unittest
import datetime
from pprint import pprint

from pytz import utc, timezone
from zope.testing import doctest
from zope.app.testing import ztapi, setup
from zope.publisher.browser import TestRequest
from zope.interface import implements, Interface
from zope.component import adapts
from zope.app.testing.setup import setUpAnnotations

from schooltool.timetable import ITimetables
from schooltool.timetable import TimetableActivity
from schooltool.timetable.model import TimetableCalendarEvent
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.course.interfaces import ISection
from schooltool.relationship.tests import setUpRelationships
from schooltool.testing.util import fakePath


class StubTimetables(object):
    adapts(Interface)
    implements(ITimetables)
    def __init__(self, context):
        self.context = context

    def makeTimetableCalendar(self):
        return ImmutableCalendar([
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 14, 10, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Math", period_id="A", activity=None),
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 14, 11, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Arts", period_id="D", activity=None),
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Math", period_id="B", activity=None),
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Arts",
                period_id="C", activity=None),
            ])


def doctest_verifyPeriodForSection():
    """Doctest for verifyPeriodForSection

    When traversing to the realtime attendance form, we want to verify
    that the section has the given period takes place on the given
    date.  We have a utility function for that:

        >>> from schooltool.attendance.browser.attendance import \\
        ...     verifyPeriodForSection

        >>> section = StubTimetables(None)

    Now we can try our helper function:

        >>> for date in [datetime.date(2005, 12, d) for d in (14, 15, 16)]:
        ...     for period_id in 'A', 'B', 'C', 'D':
        ...         result = verifyPeriodForSection(section, date,
        ...                                         period_id, utc)
        ...         print date, period_id, result
        2005-12-14 A True
        2005-12-14 B False
        2005-12-14 C False
        2005-12-14 D True
        2005-12-15 A False
        2005-12-15 B True
        2005-12-15 C True
        2005-12-15 D False
        2005-12-16 A False
        2005-12-16 B False
        2005-12-16 C False
        2005-12-16 D False

    """

def doctest_SectionAttendanceTraverserPlugin():
    r"""Tests for SectionAttendanceTraverserPlugin

    We need an ITimetables adapter in order to verify that a given
    period is valid for a given day:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

        >>> from schooltool.attendance.browser.attendance import \
        ...          SectionAttendanceTraverserPlugin
        >>> from schooltool.traverser.interfaces import ITraverserPlugin

        >>> ITraverserPlugin.implementedBy(SectionAttendanceTraverserPlugin)
        True

    If we traverse a name this plugin does not handle, we get a
    NotFound error.

        >>> plugin = SectionAttendanceTraverserPlugin("request", "context")
        >>> plugin.publishTraverse(None, 'name')
        Traceback (most recent call last):
        ...
        NotFound: Object: 'request', name: 'name'

    We must register the view we are traversing to first:

        >>> class AttendanceViewStub(object):
        ...     def __init__(self, context, request): pass
        ...     def __repr__(self):
        ...         return "%s, %s" % (self.date, self.period_id)
        >>> ztapi.browserView(None, 'attendance', AttendanceViewStub)

    Now we can try the typical case:

        >>> request = TestRequest()
        >>> request.setTraversalStack(['B', '2005-12-15'])
        >>> plugin.publishTraverse(request, "attendance")
        2005-12-15, B

        >>> request.getTraversalStack()
        []

    If there are more elements on the traversal stack, they remain there:

        >>> request.setTraversalStack(['extra', 'C', '2005-12-15'])
        >>> plugin.publishTraverse(request, "attendance")
        2005-12-15, C

        >>> request.getTraversalStack()
        ['extra']

    What if the date is invalid?

        >>> request.setTraversalStack(['A', '2005-02-29'])
        >>> plugin.publishTraverse(request, "attendance")
        Traceback (most recent call last):
          ...
        NotFound: Object: 'request', name: 'attendance'

    What if the period is invalid?

        >>> request.setTraversalStack(['A', '2005-12-15'])
        >>> plugin.publishTraverse(request, "attendance")
        Traceback (most recent call last):
          ...
        NotFound: Object: 'request', name: 'attendance'

    If there are no date and period id following, we also get a NotFound:

        >>> request.setTraversalStack([])
        >>> plugin.publishTraverse(request, "attendance")
        Traceback (most recent call last):
          ...
        NotFound: Object: 'request', name: 'attendance'

    """


class CalendarEventViewletManagerStub(object):
    pass


class EventForDisplayStub(object):
    def __init__(self, event, tz=utc):
        self.context = event
        self.dtstarttz = event.dtstart.astimezone(tz)


class SectionStub(object):
    implements(ISection)


class PersonStub(object):
    pass


def doctest_AttendanceCalendarEventViewlet():
    r"""Tests for AttendanceCalendarEventViewlet

        >>> from schooltool.attendance.browser.attendance \
        ...     import AttendanceCalendarEventViewlet
        >>> viewlet = AttendanceCalendarEventViewlet()
        >>> viewlet.request = TestRequest()

    Viewlets have a ``manager`` attribute that points to the viewlet manager.

        >>> viewlet.manager = CalendarEventViewletManagerStub()

    CalendarEventViewletManagerStub exports an ``event`` attribute, which
    provides IEventForDisplay.  Section meeting events are all
    ITimetableCalendarEvent.

        >>> section = SectionStub()
        >>> fakePath(section, u'/sections/math4a')
        >>> activity = TimetableActivity(title="Math", owner=section)
        >>> section_event = TimetableCalendarEvent(
        ...     datetime.datetime(2005, 12, 16, 16, 15, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", period_id="P4", activity=activity)
        >>> viewlet.manager.event = EventForDisplayStub(section_event)

    The viewlet knows how to compute a link to the section attendance form

        >>> viewlet.attendanceLink()
        'http://127.0.0.1/sections/math4a/attendance/2005-12-16/P4'

    The date in the link depends on the configured timezone

        >>> tokyo = timezone('Asia/Tokyo')
        >>> viewlet.manager.event = EventForDisplayStub(section_event, tokyo)
        >>> viewlet.manager.event.dtstarttz
        datetime.datetime(2005, 12, 17, 1, 15, ...)
        >>> viewlet.attendanceLink()
        'http://127.0.0.1/sections/math4a/attendance/2005-12-17/P4'

    If the event is not a section meeting event, the link is empty

        >>> person = PersonStub()
        >>> activity = TimetableActivity(title="Math study", owner=person)
        >>> nonsection_event = TimetableCalendarEvent(
        ...     datetime.datetime(2005, 12, 16, 16, 15, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     activity.title, period_id="P3", activity=activity)
        >>> viewlet.manager.event = EventForDisplayStub(nonsection_event)
        >>> viewlet.attendanceLink()

    The link is also empty if the event is not a timetable event.

        >>> random_event = SimpleCalendarEvent(
        ...     datetime.datetime(2005, 12, 16, 16, 15, tzinfo=utc),
        ...     datetime.timedelta(minutes=15),
        ...     "Snacks")
        >>> viewlet.manager.event = EventForDisplayStub(random_event)
        >>> viewlet.attendanceLink()

    """


def doctest_RealtimeAttendanceView_listMembers():
    """Test for RealtimeAttendanceView.listMembers

    First, let's register getSectionAttendance as an adapter:

        >>> from schooltool.attendance.interfaces import ISectionAttendance
        >>> from schooltool.attendance.attendance import getSectionAttendance
        >>> from schooltool.person.interfaces import IPerson
        >>> ztapi.provideAdapter(IPerson, ISectionAttendance,
        ...                      getSectionAttendance)

    Let's set up a view:

        >>> from schooltool.attendance.browser.attendance import \\
        ...     RealtimeAttendanceView
        >>> from schooltool.course.section import Section
        >>> section = Section()
        >>> view = RealtimeAttendanceView(section, TestRequest())
        >>> view.date = datetime.date(2005, 12, 15)

    If the section does not have any members, listMembers returns an
    empty list:

        >>> view.listMembers()
        []

    Let's add some students:

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person, PersonContainer
        >>> person1 = Person('person1', title='Person1')
        >>> person2 = Person('person2', title='Person2')
        >>> person3 = Person('person3', title='Person3')
        >>> person4 = Person('person4', title='Person4')

        >>> persons = PersonContainer()
        >>> persons[''] = person1
        >>> persons[''] = person2
        >>> persons[''] = person3
        >>> persons[''] = person4

        >>> section.members.add(person1)
        >>> section.members.add(person2)


    These members should appear in the output

        >>> pprint(view.listMembers())
        [(u'person1', 'Person1', 'attendance-clear'),
         (u'person2', 'Person2', 'attendance-clear')]

    So should transitive members:

        >>> form = Group('Form1')
        >>> form.members.add(person3)
        >>> form.members.add(person4)
        >>> section.members.add(form)

        >>> pprint(view.listMembers())
        [(u'person1', 'Person1', 'attendance-clear'),
         (u'person2', 'Person2', 'attendance-clear'),
         (u'person3', 'Person3', 'attendance-clear'),
         (u'person4', 'Person4', 'attendance-clear')]

    Let's add an absence record to one person:

        >>> attendance = ISectionAttendance(person4)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', False)

    Now the members' list displays a new status:

        >>> pprint(view.listMembers())
        [(u'person1', 'Person1', 'attendance-clear'),
         (u'person2', 'Person2', 'attendance-clear'),
         (u'person3', 'Person3', 'attendance-clear'),
         (u'person4', 'Person4', 'attendance-absent')]

    """

def doctest_RealtimeAttendanceView_studentStatus():
    """Tests for RealtimeAttendanceView.studentStatus

    First, let's register getSectionAttendance as an adapter:

        >>> from schooltool.attendance.interfaces import ISectionAttendance
        >>> from schooltool.attendance.attendance import getSectionAttendance
        >>> from schooltool.person.interfaces import IPerson
        >>> ztapi.provideAdapter(IPerson, ISectionAttendance,
        ...                      getSectionAttendance)


        >>> from schooltool.attendance.browser.attendance import \\
        ...     RealtimeAttendanceView
        >>> from schooltool.course.section import Section
        >>> section = Section()
        >>> view = RealtimeAttendanceView(section, TestRequest())
        >>> view.date = datetime.date(2005, 12, 15)

    Let's add some members to the group:

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person, PersonContainer
        >>> person1 = Person('person1', title='Person1')
        >>> person2 = Person('person2', title='Person2')
        >>> person3 = Person('person3', title='Person3')
        >>> person4 = Person('person4', title='Person4')

        >>> persons = PersonContainer()
        >>> persons[''] = person1
        >>> persons[''] = person2
        >>> persons[''] = person3
        >>> persons[''] = person4

        >>> section.members.add(person1)
        >>> section.members.add(person2)

    Initially the student's absence is 'clear' (no records):

        >>> view.studentStatus(person1)
        'attendance-clear'

    Let's record an unexplained absence for the student:

        >>> attendance = ISectionAttendance(person1)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', False)

    Now that the student has an unexplained absence, and no presence
    records, the status is 'absent':

        >>> view.studentStatus(person1)
        'attendance-absent'

    If we add a presence record for the same day, the status becomes 'alert':

        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'C', True)
        >>> view.studentStatus(person1)
        'attendance-alert'

    Let's take another student.  It's a good student, she's been
    present to all sections:

        >>> attendance = ISectionAttendance(person2)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', True)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'C', True)
        >>> view.studentStatus(person2)
        'attendance-present'

    Let's take another yet student.  He's broken his leg and is
    excused for the whole two months:

        >>> attendance = ISectionAttendance(person3)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', False)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'C', False)
        >>> for record in attendance.getAllForDay(view.date):
        ...     expn = record.addExplanation("Broken leg")
        ...     expn.accept()
        >>> view.studentStatus(person3)
        'attendance-explained'

    Yet another student was tardy.  The status shows that he's been absent:

        >>> attendance = ISectionAttendance(person4)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', False)
        >>> ar = attendance.getAllForDay(view.date).next()
        >>> ar.makeTardy(datetime.datetime(2005, 12, 15, 10, 9, tzinfo=utc))
        >>> view.studentStatus(person4)
        'attendance-absent'

    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpTraversal()
    setUpAnnotations()
    setUpRelationships()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    return doctest.DocTestSuite(optionflags=doctest.ELLIPSIS,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')