#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for schooltool.browser.app

$Id$
"""

import unittest
from logging import INFO
from datetime import date, time, timedelta

from zope.testing.doctest import DocTestSuite
from schooltool.browser.tests import TraversalTestMixin, RequestStub, setPath
from schooltool.tests.utils import EqualsSortedMixin
from schooltool.tests.utils import AppSetupMixin

__metaclass__ = type


class GroupStub:

    def __init__(self, title='Group X', __name__='grp_x'):
        self.__name__ = __name__
        self.title = title


class PersonStub:
    __name__ = 'manager'
    title = 'The Mgmt'


class TestAppView(unittest.TestCase, TraversalTestMixin):

    def createView(self):
        from schooltool.app import Application
        from schooltool.app import ApplicationObjectContainer
        from schooltool.model import Person, Group, Resource, Note
        from schooltool.browser.app import RootView
        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        app['groups'] = ApplicationObjectContainer(Group)
        app['resources'] = ApplicationObjectContainer(Resource)
        app['notes'] = ApplicationObjectContainer(Note)
        view = RootView(app)
        return view

    def createRequestWithAuthentication(self, *args, **kw):
        from schooltool.interfaces import AuthenticationError
        person = PersonStub()
        setPath(person, '/persons/manager')
        request = RequestStub(*args, **kw)
        def authenticate(username, password):
            if username == 'manager' and password == 'schooltool':
                request.authenticated_user = person
                request.user = username
            else:
                request.authenticated_user = None
                request.user = ''
                raise AuthenticationError
        request.authenticate = authenticate
        return request

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assert_('Username' in result)
        self.assert_('error' not in result)
        self.assert_('expired' not in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_render_expired(self):
        view = self.createView()
        request = RequestStub('/?expired=1', args={'expired': '1'})
        result = view.render(request)
        self.assert_('Username' in result)
        self.assert_('error' not in result)
        self.assert_('expired' in result)
        self.assert_('action="/"' in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_render_forbidden(self):
        view = self.createView()
        request = RequestStub('/?forbidden=1', args={'forbidden': '1'},
                              authenticated_user=PersonStub())
        result = view.render(request)
        self.assert_('Username' in result)
        self.assert_('expired' not in result)
        self.assert_('not allowed' in result)
        self.assert_('action="/"' in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_render_with_url(self):
        view = self.createView()
        request = RequestStub(args={'url': '/some/url'})
        result = view.render(request)
        self.assert_('Username' in result)
        self.assert_('error' not in result)
        self.assert_('expired' not in result)
        self.assert_('<input type="hidden" name="url" value="/some/url" />'
                     in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_render_already_logged_in(self):
        view = self.createView()
        request = RequestStub(authenticated_user='the_boss')
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/start')

    def test_post(self):
        from schooltool.component import getTicketService
        view = self.createView()
        request = self.createRequestWithAuthentication(method='POST',
                              args={'username': 'manager',
                                    'password': 'schooltool'})
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/start')
        ticket = request._outgoing_cookies['auth']
        username, password = \
                  getTicketService(view.context).verifyTicket(ticket)
        self.assertEquals(username, 'manager')
        self.assertEquals(password, 'schooltool')

    def test_post_with_url(self):
        from schooltool.component import getTicketService
        view = self.createView()
        request = self.createRequestWithAuthentication(method='POST',
                              args={'username': 'manager',
                                    'password': 'schooltool',
                                    'url': '/some/path'})
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/some/path')
        ticket = request._outgoing_cookies['auth']
        username, password = \
                  getTicketService(view.context).verifyTicket(ticket)
        self.assertEquals(username, 'manager')
        self.assertEquals(password, 'schooltool')

    def test_post_failed(self):
        view = self.createView()
        request = self.createRequestWithAuthentication(method='POST',
                              args={'username': 'manager',
                                    'password': '5ch001t001'})
        result = view.render(request)
        self.assert_('error' in result)
        self.assert_('Username' in result)
        self.assert_('manager' in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_traversal(self):
        from schooltool.browser import StaticFile
        from schooltool.browser.app import LogoutView
        from schooltool.browser.app import DatabaseResetView
        from schooltool.browser.app import StartView
        from schooltool.browser.app import PersonContainerView
        from schooltool.browser.app import GroupContainerView
        from schooltool.browser.app import ResourceContainerView
        from schooltool.browser.app import NoteContainerView
        from schooltool.browser.app import BusySearchView
        from schooltool.browser.applog import ApplicationLogView
        from schooltool.browser.timetable import TimetableSchemaWizard
        from schooltool.browser.timetable import TimetableSchemaServiceView
        from schooltool.browser.timetable import TimePeriodServiceView
        from schooltool.browser.timetable import NewTimePeriodView
        from schooltool.browser.csv import CSVImportView

        view = self.createView()
        app = view.context
        self.assertTraverses(view, 'logout', LogoutView, app)
        self.assertTraverses(view, 'reset_db.html', DatabaseResetView, app)
        self.assertTraverses(view, 'applog', ApplicationLogView, app)
        self.assertTraverses(view, 'persons', PersonContainerView,
                             app['persons'])
        self.assertTraverses(view, 'groups', GroupContainerView, app['groups'])
        self.assertTraverses(view, 'resources', ResourceContainerView,
                             app['resources'])
        self.assertTraverses(view, 'notes', NoteContainerView,
                             app['notes'])
        self.assertTraverses(view, 'csvimport.html', CSVImportView, app)
        self.assertTraverses(view, 'busysearch', BusySearchView, app)
        self.assertTraverses(view, 'ttschemas', TimetableSchemaServiceView,
                             app.timetableSchemaService)
        self.assertTraverses(view, 'newttschema', TimetableSchemaWizard,
                             app.timetableSchemaService)
        self.assertTraverses(view, 'time-periods', TimePeriodServiceView,
                             app.timePeriodService)
        view2 = self.assertTraverses(view, 'newtimeperiod', NewTimePeriodView,
                                    None)
        self.assert_(view2.service is app.timePeriodService)
        css = self.assertTraverses(view, 'schooltool.css', StaticFile)
        self.assertEquals(css.content_type, 'text/css')
        for picture in ('logo.png', 'group.png', 'person.png', 'resource.png'):
            image = self.assertTraverses(view, picture, StaticFile)
            self.assertEquals(image.content_type, 'image/png')
        user = object()
        request = RequestStub(authenticated_user=user)
        self.assertTraverses(view, 'start', StartView, user, request=request)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())


class TestLogoutView(unittest.TestCase):

    def createView(self):
        from schooltool.browser.app import LogoutView
        from schooltool.app import Application
        view = LogoutView(Application())
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/')

    def test_render_with_auth(self):
        from schooltool.component import getTicketService
        from schooltool.interfaces import AuthenticationError
        view = self.createView()
        ticket = getTicketService(view.context).newTicket(('usr', 'pwd'))
        request = RequestStub(cookies={'auth': ticket})
        request.authenticate = lambda username, password: None
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/')
        self.assertRaises(AuthenticationError,
                          getTicketService(view.context).verifyTicket, ticket)


class TestStartView(unittest.TestCase):

    def createView(self):
        from schooltool.browser.app import StartView
        from schooltool.model import Person
        user = Person()
        setPath(user, '/persons/user')
        return StartView(user)

    def test(self):
        view = self.createView()
        request = RequestStub(authenticated_user=view.context)
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assertEquals(request.code, 200)


class TestPersonAddView(unittest.TestCase):

    def createView(self):
        from schooltool.model import Person
        from schooltool.browser.app import PersonAddView

        class PersonContainerStub:

            def __init__(self):
                self.persons = {}

            def keys(self):
                return self.persons.keys()

            def itervalues(self):
                return self.persons.itervalues()

            def new(self, username, title):
                if username is None:
                    username = 'auto'
                if username in self.persons:
                    raise KeyError(username)
                person = Person(title=title)
                person.__name__ = username
                person.__parent__ = self
                self.persons[username] = person
                return person

        self.person_container = PersonContainerStub()
        setPath(self.person_container, '/persons')

        return PersonAddView(self.person_container)

    def test(self):
        view = self.createView()
        view.request = RequestStub()
        result = view.do_GET(view.request)
        assert 'Add person' in result

    def test_name_validator(self):
        view = self.createView()
        view.name_validator(None)
        view.name_validator('')
        view.name_validator('xyzzy')
        self.assertRaises(ValueError, view.name_validator, 'xy zzy')
        self.assertRaises(ValueError, view.name_validator, u'\u00ff')
        view.context.new('existing', 'Some Title')
        self.assertRaises(ValueError, view.name_validator, 'existing')

    def test_processForm_no_input(self):
        view = self.createView()
        request = RequestStub()
        assert not view._processForm(request)
        assert 'required' in view.first_name_widget.error
        assert 'required' in view.last_name_widget.error

    def test_processForm_just_required_fields(self):
        view = self.createView()
        request = RequestStub(args={'first_name': 'First',
                                    'last_name': 'Last'})
        assert view._processForm(request)
        self.assertEquals(view.first_name_widget.value, u'First')
        self.assertEquals(view.last_name_widget.value, u'Last')

    def test_processForm_password_mismatch(self):
        view = self.createView()
        request = RequestStub(args={'first_name': 'First',
                                    'last_name': 'Last',
                                    'optional_password': 'pwd',
                                    'confirm_password': 'badpwd'})
        assert not view._processForm(request)
        assert 'do not match' in view.confirm_password_widget.error

    def test_processForm_all_fields(self):
        view = self.createView()
        request = RequestStub(args={'first_name': 'First',
                                    'last_name': 'Last',
                                    'optional_username': 'usrnm',
                                    'optional_password': 'pwd',
                                    'confirm_password': 'pwd',
                                    'date_of_birth': '1975-01-02',
                                    'comment': 'It was a long day.'})
        assert view._processForm(request)
        self.assertEquals(view.first_name_widget.value, u'First')
        self.assertEquals(view.last_name_widget.value, u'Last')
        self.assertEquals(view.username_widget.value, u'usrnm')
        self.assertEquals(view.password_widget.value, u'pwd')
        self.assertEquals(view.dob_widget.value, date(1975, 1, 2))
        self.assertEquals(view.comment_widget.value, u'It was a long day.')

    def test_processForm_with_an_error(self):
        view = self.createView()
        request = RequestStub(args={'first_name': 'First',
                                    'last_name': 'Last',
                                    'optional_username': 'usrnm',
                                    'optional_password': 'pwd',
                                    'confirm_password': 'pwd',
                                    'date_of_birth': '1975-I-02',
                                    'comment': 'It was a long day.'})
        assert not view._processForm(request)
        assert view.dob_widget.error

    def test_processPhoto_no_photo(self):
        view = self.createView()
        request = RequestStub()
        assert view._processPhoto(request) is None
        assert not view.error

    def test_processPhoto_photo(self):
        view = self.createView()
        request = RequestStub(args={'photo': 'P6\n1 1\n255\n\xff\xff\xff'})
        assert view._processPhoto(request) is not None
        assert not view.error

    def test_processPhoto_bad_photo(self):
        view = self.createView()
        request = RequestStub(args={'photo': 'This is not an image'})
        assert view._processPhoto(request) is None
        assert 'Invalid photo' in view.error

    def do_test_addUser(self, username, password,
                        expect_username, expect_password):
        view = self.createView()
        view.request = RequestStub()
        person = view._addUser(username, password)
        assert person is not None
        self.assertEquals(person.__name__, expect_username)
        self.assertEquals(person.title, expect_username)
        if expect_password:
            assert person.hasPassword()
        else:
            assert not person.hasPassword()
        self.assertEquals(view.request.applog,
                          [(None, u'Object /persons/%s of type Person created'
                                  % expect_username, INFO)])

    def test_addUser_no_credentials(self):
        for username, password in [(None, None), ('', '')]:
            self.do_test_addUser(username, password, "auto", False)

    def test_addUser_no_password(self):
        username = 'someone'
        for password in [None, '']:
            self.do_test_addUser(username, password, username, False)

    def test_addUser_no_username(self):
        password = 'pwd'
        for username in [None, '']:
            self.do_test_addUser(username, password, 'auto', True)

    def test_addUser_with_credentials(self):
        username = 'someone'
        password = 'pwd'
        self.do_test_addUser(username, password, username, True)

    def test_addUser_conflict(self):
        view = self.createView()
        view.context.new('existing', 'Existing User')
        view.request = RequestStub()
        person = view._addUser('existing', 'doesnotmatter')
        assert person is None
        self.assertEquals(view.request.applog, [])

    def test_setUserInfo(self):
        from schooltool.component import FacetManager
        view = self.createView()
        view.request = RequestStub()
        person = view.context.new('person', 'Some Person')
        view._setUserInfo(person, 'John', 'Major', date(1980, 4, 13),
                          'No comment.')
        self.assertEquals(person.title, 'John Major')
        info = FacetManager(person).facetByName('person_info')
        self.assertEquals(info.first_name, u'John')
        self.assertEquals(info.last_name, u'Major')
        self.assertEquals(info.date_of_birth, date(1980, 4, 13))
        self.assertEquals(info.comment, u'No comment.')
        self.assertEquals(view.request.applog,
                          [(None, u'Person info updated on John Major'
                                   ' (/persons/person)', INFO)])

    def test_setUserPhoto_no_photo(self):
        from schooltool.component import FacetManager
        view = self.createView()
        view.request = RequestStub()
        person = view.context.new('person', 'Some Person')
        info = FacetManager(person).facetByName('person_info')
        view._setUserPhoto(person, None)
        assert info.photo is None
        self.assertEquals(view.request.applog, [])

    def test_setUserPhoto_photo(self):
        from schooltool.component import FacetManager
        view = self.createView()
        view.request = RequestStub()
        person = view.context.new('person', 'Some Person')
        info = FacetManager(person).facetByName('person_info')
        view._setUserPhoto(person, 'pretend jpeg')
        self.assertEquals(info.photo, 'pretend jpeg')
        self.assertEquals(view.request.applog,
                          [(None, u'Photo added on Some Person'
                                   ' (/persons/person)', INFO)])

    def test_POST_no_data(self):
        view = self.createView()
        view.request = RequestStub()
        result = view.do_POST(view.request)
        assert 'error' in result
        self.assertEquals(view.request.applog, [])

    def test_POST_username_conflict(self):
        view = self.createView()
        view.context.new('existing', 'doesnotmatter')
        view.request = RequestStub(args={'first_name': 'First',
                                         'last_name': 'Last',
                                         'optional_username': 'existing'})
        result = view.do_POST(view.request)
        assert 'User with this username already exists' in result
        self.assertEquals(view.request.applog, [])

    def test_POST_realname_conflict(self):
        from schooltool.component import FacetManager
        view = self.createView()
        person = view.context.new('existing', 'doesnotmatter')
        info = FacetManager(person).facetByName('person_info')
        info.first_name = 'First'
        info.last_name = 'Last'
        view.request = RequestStub(args={'first_name': 'First',
                                         'last_name': 'Last'})
        result = view.do_POST(view.request)
        self.assertEquals(view.error, 'User with this name already exists.')
        self.assertEquals(view.request.applog, [])
        assert 'CONFIRM' in result

    def test_POST_realname_conflict_overriden_by_user(self):
        from schooltool.component import FacetManager
        view = self.createView()
        person = view.context.new('existing', 'doesnotmatter')
        info = FacetManager(person).facetByName('person_info')
        info.first_name = 'First'
        info.last_name = 'Last'
        view.request = RequestStub(args={'first_name': 'First',
                                         'last_name': 'Last',
                                         'CONFIRM': 'Add anyway'})
        result = view.do_POST(view.request)
        assert not view.error
        assert view.request.applog

    def test_POST_realname_conflict_canceled(self):
        from schooltool.component import FacetManager
        view = self.createView()
        person = view.context.new('existing', 'doesnotmatter')
        info = FacetManager(person).facetByName('person_info')
        info.first_name = 'George'
        info.last_name = 'Last'
        view.request = RequestStub(args={'first_name': 'George',
                                         'last_name': 'Last',
                                         'CANCEL': 'Cancel'})
        result = view.do_POST(view.request)
        assert not view.error
        assert not view.request.applog
        assert 'George' not in result

    def test_POST_bad_photo(self):
        view = self.createView()
        view.request = RequestStub(args={'first_name': 'First',
                                         'last_name': 'Last',
                                         'photo': 'bad image data'})
        result = view.do_POST(view.request)
        assert 'error' in result
        self.assertEquals(view.request.applog, [])

    def test_POST_success(self):
        view = self.createView()
        view.request = RequestStub(args={'first_name': 'First',
                                         'last_name': 'Last'})
        result = view.do_POST(view.request)
        request = view.request
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/auto/edit.html')
        self.assertEquals(request.applog,
                          [(None, u'Object /persons/auto of type'
                                   ' Person created', INFO),
                           (None, u'Person info updated on First Last'
                                   ' (/persons/auto)', INFO)])


class TestObjectContainerView(unittest.TestCase, TraversalTestMixin):

    def setUp(self):
        from schooltool.browser.app import ObjectContainerView

        class ViewStub:

            def __init__(self, context):
                self.context = context

        class AddViewStub:

            def __init__(self, context):
                self.context = context

        # These can be overridden by subclasses.
        self.view = ObjectContainerView
        self.add_view = ViewStub
        self.obj_view = AddViewStub

    def createView(self):
        from schooltool.app import Application
        from schooltool.app import ApplicationObjectContainer
        from schooltool.model import Person
        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        app['persons'].new('obj', title='Some Object')
        self.obj = app['persons']['obj']

        view = self.view(app['persons'])
        view.add_view = self.add_view
        view.obj_view = self.obj_view
        return view

    def test_render_index(self):
        view = self.createView()
        view.isManager = lambda: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        for s in ['href="http://localhost:7001/persons/obj"',
                  'Some Object',
                  'href="http://localhost:7001/persons/add.html"',
                  view.index_title,
                  view.add_title]:
            self.assert_(s in result, s)

        view.isManager = lambda: False
        self.assert_('add.html' not in view.render(request))

    def test_traverse(self):
        view = self.createView()
        self.assertTraverses(view, 'obj', self.obj_view, self.obj)
        self.assertTraverses(view, 'add.html', self.add_view, view.context)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())

    def test_sortedObjects(self):
        view = self.createView()
        o1 = GroupStub(__name__='a', title='ccc')
        o2 = GroupStub(__name__='b', title='bbb')
        o3 = GroupStub(__name__='c', title='aaa')
        view.context.itervalues = lambda: [o1, o2, o3]
        objs = view.sortedObjects()
        self.assertEquals(objs, [o3, o2, o1])


class TestPersonContainerView(TestObjectContainerView):

    def setUp(self):
        from schooltool.browser.app import PersonContainerView, PersonAddView
        from schooltool.browser.model import PersonView
        TestObjectContainerView.setUp(self)
        self.view = PersonContainerView
        self.add_view = PersonAddView
        self.obj_view = PersonView


class TestGroupContainerView(TestObjectContainerView):

    def setUp(self):
        from schooltool.browser.app import GroupContainerView, GroupAddView
        from schooltool.browser.model import GroupView
        TestObjectContainerView.setUp(self)
        self.view = GroupContainerView
        self.add_view = GroupAddView
        self.obj_view = GroupView


class TestResourceContainerView(TestObjectContainerView):

    def setUp(self):
        from schooltool.browser.app import ResourceContainerView
        from schooltool.browser.app import ResourceAddView
        from schooltool.browser.model import ResourceView
        TestObjectContainerView.setUp(self)
        self.view = ResourceContainerView
        self.add_view = ResourceAddView
        self.obj_view = ResourceView


class TestNoteContainerView(TestObjectContainerView):

    def setUp(self):
        from schooltool.browser.app import NoteContainerView
        from schooltool.browser.app import NoteAddView
        from schooltool.browser.model import NoteView
        TestObjectContainerView.setUp(self)
        self.view = NoteContainerView
        self.add_view = NoteAddView
        self.obj_view = NoteView


class TestObjectAddView(AppSetupMixin, unittest.TestCase):

    def createView(self):
        from schooltool.browser.app import ObjectAddView
        from schooltool.model import ApplicationObjectMixin

        class ObjContainerStub:

            def __init__(self):
                self.objs = []

            def new(self, name, title):
                if name == 'conflict':
                    raise KeyError(name)
                obj = ApplicationObjectMixin(title=title)
                if name is None:
                    name = "auto"
                obj.__name__ = name
                obj.__parent__ = self
                self.objs.append(obj)
                return obj

            def itervalues(self):
                return iter(self.objs)

        self.container = ObjContainerStub()
        setPath(self.container, '/objects')
        return ObjectAddView(self.container)

    def test_GET(self):
        view = self.createView()
        request = RequestStub()
        view.request = request
        content = view.do_GET(request)
        self.assert_('Add object' in content)

    def test_POST(self):
        view = self.createView()
        request = RequestStub(args={'name': 'newobj',
                                    'title': 'New \xc4\x85 stuff'})
        view.request = request
        content = view.do_POST(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/objects/newobj')
        self.assertEquals(request.applog,
                          [(None, u'Object /objects/newobj of type'
                            ' ApplicationObjectMixin created', INFO)])

        self.assertEquals(len(self.container.objs), 1)
        obj = self.container.objs[0]
        self.assertEquals(obj.__name__, 'newobj')
        self.assertEquals(obj.title, u'New \u0105 stuff')

    def test_POST_with_parent(self):
        from schooltool.browser.app import ObjectAddView
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URIMember
        view = ObjectAddView(self.app['resources'])
        teachers = self.teachers
        view.parent = teachers
        request = RequestStub(args={'name': 'newobj',
                                    'title': 'New \xc4\x85 stuff'})
        view.request = request
        content = view.do_POST(request)
        obj = self.app['resources']['newobj']
        assert obj in getRelatedObjects(teachers, URIMember)
        self.assertEquals(view.request.applog,
                [(None, u"Object /resources/newobj of type"
                         " Resource created", INFO),
                 (None, u"Relationship 'Membership' between "
                         "/resources/newobj and /groups/teachers created",
                  INFO)])

    def test_POST_cancel(self):
        view = self.createView()
        request = RequestStub(args={'name': 'newobj',
                                    'title': 'New \xc4\x85 stuff',
                                    'CANCEL': 'Cancel'})
        view.request = request
        content = view.do_POST(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog, [])

    def test_POST_noname(self):
        view = self.createView()
        request = RequestStub(args={'name': '',
                                    'title': 'something'})
        view.request = request
        content = view.do_POST(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/objects/auto')
        self.assertEquals(request.applog,
                          [(None, u'Object /objects/auto of type'
                            ' ApplicationObjectMixin created', INFO)])

        self.assertEquals(len(self.container.objs), 1)
        obj = self.container.objs[0]
        self.assertEquals(obj.__name__, 'auto')
        self.assertEquals(obj.title, u'something')

    def test_POST_notitle(self):
        view = self.createView()
        request = RequestStub(args={'name': '',
                                    'title': ''})
        view.request = request
        content = view.do_POST(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog, [])
        self.assert_('Add object' in content)
        self.assert_('Title should not be empty' in content)

    def test_POST_duptitle(self):
        view = self.createView()
        view.context.new(name="obj1", title="Already Used")
        request = RequestStub(args={'name': '',
                                    'title': 'Already Used'})
        view.request = request
        content = view.do_POST(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog, [])
        self.assert_('Add object' in content)
        self.assert_('There is an object with this title already' in content)

    def test_POST_duptitle_anyway(self):
        view = self.createView()
        view.context.new(name="obj1", title="Already Used")
        request = RequestStub(args={'name': 'newobj',
                                    'title': 'Already Used',
                                    'CONFIRM': 'Add anyway'})
        view.request = request
        content = view.do_POST(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/objects/newobj')
        self.assertEquals(request.applog,
                          [(None, u'Object /objects/newobj of type'
                            ' ApplicationObjectMixin created', INFO)])

        self.assertEquals(len(self.container.objs), 2)
        obj = self.container.objs[-1]
        self.assertEquals(obj.__name__, 'newobj')
        self.assertEquals(obj.title, u'Already Used')

    def test_POST_errors(self):
        view = self.createView()
        request = RequestStub(args={'name': 'new/obj', 'title': 'abc'})
        view.request = request
        content = view.do_POST(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog, [])
        self.assert_('Add object' in content)
        self.assert_('Invalid identifier' in content)

    def test_POST_conflict(self):
        view = self.createView()
        request = RequestStub(args={'name': 'conflict', 'title': 'foofoobar'})
        view.request = request
        content = view.do_POST(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog, [])
        self.assert_('Add object' in content)
        self.assert_('Identifier already taken' in content)
        self.assert_('conflict' in content)
        self.assert_('foofoobar' in content)

    def test_titleAlreadyUsed(self):
        view = self.createView()
        view.context.new(name='obj1', title='Used Already')
        assert view._titleAlreadyUsed('Used Already')
        assert not view._titleAlreadyUsed('Not Used Yet')


class TestGroupAddView(AppSetupMixin, unittest.TestCase):

    def createView(self):
        from schooltool.browser.app import GroupAddView
        view = GroupAddView(self.app['groups'])
        return view

    def test(self):
        view = self.createView()
        self.assertEquals(view.title, "Add group")

    def test_GET(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager,
                              args={'parentgroup': 'teachers'})
        result = view.render(request)
        self.assertEquals(view.title, "Add group (a subgroup of Teachers)")
        assert ('<input type="hidden" name="parentgroup"'
                      ' value="teachers"' in result), result

    def test_POST_with_parentgroup(self):
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URIMember
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager,
                              method='POST',
                              args={'title': 'New Group', 'name': 'newgrp',
                                    'parentgroup': 'teachers'})
        result = view.render(request)
        self.assertEquals(request.code, 302)
        newgrp = self.app["groups"]["newgrp"]
        assert newgrp in getRelatedObjects(self.teachers, URIMember)

    def test_processExtraFormFields_no_parent_specified(self):
        view = self.createView()
        request = RequestStub()
        view._processExtraFormFields(request)
        assert view.parent is None
        self.assertEquals(view.title, "Add group")

    def test_processExtraFormFields_parent_specified(self):
        view = self.createView()
        request = RequestStub(args={'parentgroup': 'teachers'})
        view._processExtraFormFields(request)
        assert view.parent is self.teachers
        self.assertEquals(view.title, "Add group (a subgroup of Teachers)")

    def test_processExtraFormFields_parent_does_not_exist(self):
        view = self.createView()
        request = RequestStub(args={'parentgroup': 'no such group'})
        view._processExtraFormFields(request)
        assert view.parent is None
        self.assertEquals(view.title, "Add group")


class TestResourceAddView(AppSetupMixin, unittest.TestCase):

    def createView(self):
        from schooltool.browser.app import ResourceAddView
        view = ResourceAddView(self.app['resources'])
        return view

    def test(self):
        view = self.createView()
        self.assertEquals(view.title, "Add resource")

    def test_processExtraFormFields_not_location(self):
        view = self.createView()
        request = RequestStub(args={})
        view._processExtraFormFields(request)
        assert view.parent is None
        assert not view.prev_location

    def test_processExtraFormFields_parent_does_not_exist(self):
        view = self.createView()
        request = RequestStub(args={'location': ''})
        view._processExtraFormFields(request)
        assert view.parent is self.locations
        assert view.prev_location


class TestNoteAddView(AppSetupMixin, unittest.TestCase):
      
    def createView(self):
        from schooltool.browser.app import NoteAddView
        view = NoteAddView(self.app['notes'])
        return view
    
    def test(self):
        view = self.createView()
        self.assertEquals(view.title, "Add note")


class TestBusySearchView(unittest.TestCase, EqualsSortedMixin):

    def setUp(self):
        from schooltool.model import Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.browser.app import BusySearchView
        app = Application()
        self.app = app
        r = app['resources'] = ApplicationObjectContainer(Resource)
        self.r1 = r.new('r1', title='Resource 1')
        self.r2 = r.new('r2', title='Resource 2')
        self.view = BusySearchView(app)

    def test_allResources(self):
        self.assertEqual(self.view.allResources(), [self.r1, self.r2])

    def test_update(self):
        self.view.request = RequestStub(args={'first': '2004-08-11',
                                              'last': '2004-08-11',
                                              'duration': '30',
                                              'hours': [13, 14]})
        result = self.view.update()
        assert result is None, result

        self.assertEquals(self.view.first, date(2004, 8, 11))
        self.assertEquals(self.view.last, date(2004, 8, 11))
        self.assertEquals(self.view.duration, timedelta(minutes=30))
        self.assertEquals(self.view.hours, [(time(13, 0), timedelta(hours=2))])
        self.assertEqualsSorted(self.view.resources, [self.r1, self.r2])

    def test_listResources(self):
        self.view.request = RequestStub(args={'first': '2004-08-11',
                                              'last': '2004-08-11',
                                              'duration': '30',
                                              'hours': [13, 14]})
        result = self.view.update()
        assert result is None, result

        results = self.view.listResources()

        self.assertEquals(results,
                          [{'title': 'Resource 1',
                            'href': 'http://localhost:7001/resources/r1',
                            'slots': [{'duration': 120,
                                       'start_date': '2004-08-11',
                                       'start_time': '13:00',
                                       'start': '2004-08-11 13:00',
                                       'end': '2004-08-11 15:00'}]},
                           {'title': 'Resource 2',
                            'href': 'http://localhost:7001/resources/r2',
                            'slots': [{'duration': 120,
                                       'start_date': '2004-08-11',
                                       'start_time': '13:00',
                                       'start': '2004-08-11 13:00',
                                       'end': '2004-08-11 15:00'}]}])

    def test_render(self):
        request = RequestStub(args={}, authenticated_user=self.r1)
        result = self.view.render(request)
        assert 'Resource 1' in result, result
        assert 'Search' in result

        request = RequestStub(args={'first': '2004-08-11',
                                    'last': '2004-08-11',
                                    'duration': '30',
                                    'hours': [13, 14],
                                    'SUBMIT': 'Submit'},
                              authenticated_user=self.r1)
        result = self.view.render(request)
        assert 'Resource 1' in result, result
        assert 'Search' in result
        assert 'Book' in result
        assert '2004-08-11 13:00' in result
        assert '2004-08-11 15:00' in result


class TestDatabaseResetView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()
        import schooltool.teaching
        schooltool.teaching.setUp()

    def createView(self):
        from schooltool.browser.app import DatabaseResetView
        return DatabaseResetView(self.app)

    def createRequest(self, *args, **kw):

        class ConnectionStub:

            def __init__(self):
                self._root = {'app': None}

            def root(self):
                return self._root

        class SiteStub:

            rootName = 'app'

        request = RequestStub(*args, **kw)
        request.zodb_conn = ConnectionStub()
        request.site = SiteStub()
        return request

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager)
        content = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('Confirm' in content)

    def test_POST(self):
        from schooltool.app import Application
        view = self.createView()
        request = self.createRequest(method='POST', args={'confirm': 'yes'},
                                     authenticated_user=self.manager)
        content = view.render(request)
        new_app = request.zodb_conn.root()['app']
        self.assert_(isinstance(new_app, Application))
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/')

    def test_POST_preserves_authentication(self):
        from schooltool.component import getTicketService
        view = self.createView()
        ticket = getTicketService(self.app).newTicket(('gandalf', '123'))
        request = self.createRequest(method='POST', args={'confirm': ''},
                                     authenticated_user=self.manager,
                                     cookies={'auth': ticket})
        content = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/')
        new_app = request.zodb_conn.root()['app']
        username, password = getTicketService(new_app).verifyTicket(ticket)
        self.assertEquals(username, 'gandalf')
        self.assertEquals(password, '123')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppView))
    suite.addTest(unittest.makeSuite(TestLogoutView))
    suite.addTest(unittest.makeSuite(TestStartView))
    suite.addTest(unittest.makeSuite(TestPersonAddView))
    suite.addTest(unittest.makeSuite(TestObjectContainerView))
    suite.addTest(unittest.makeSuite(TestPersonContainerView))
    suite.addTest(unittest.makeSuite(TestGroupContainerView))
    suite.addTest(unittest.makeSuite(TestResourceContainerView))
    suite.addTest(unittest.makeSuite(TestNoteContainerView))
    suite.addTest(unittest.makeSuite(TestObjectAddView))
    suite.addTest(unittest.makeSuite(TestGroupAddView))
    suite.addTest(unittest.makeSuite(TestResourceAddView))
    suite.addTest(unittest.makeSuite(TestNoteAddView))
    suite.addTest(unittest.makeSuite(TestBusySearchView))
    suite.addTest(unittest.makeSuite(TestDatabaseResetView))
    suite.addTest(DocTestSuite('schooltool.browser.app'))
    return suite


if __name__ == '__main__':
    unittest.main()
