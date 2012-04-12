#Copyright (c) 2011,12 Walter Bender

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA


import gtk

from sugar.activity import activity
from sugar import profile
from sugar.graphics.toolbarbox import ToolbarBox
from sugar.activity.widgets import ActivityToolbarButton
from sugar.graphics.toolbarbox import ToolbarButton
from sugar.activity.widgets import StopButton
from sugar.graphics.alert import NotifyAlert
from sugar.graphics.objectchooser import ObjectChooser
from sugar.datastore import datastore
from sugar import mime

from gettext import gettext as _

from game import Game, GAME_DEFS
from toolbar_utils import separator_factory, radio_factory, label_factory, \
    button_factory, entry_factory, combo_factory

import logging
_logger = logging.getLogger('nutrition-activity')


SERVICE = 'org.sugarlabs.NutritionActivity'
IFACE = SERVICE
LABELS = [_('Match the food to its name.'),
          _('How many calories are there?'),
          _('How much should you eat?'),
          _('Is this a well-balanced meal?')]
PYRAMID = [_('sweets'), _('meat and dairy'), _('fruits and grains')]

class NutritionActivity(activity.Activity):
    """ Simple nutrition game based on GCompris ImageID """

    def __init__(self, handle):
        """ Initialize the toolbars and the game board """
        super(NutritionActivity, self).__init__(handle)

        self.path = activity.get_bundle_path()

        self._setup_toolbars()
        self._new_food_image_path = None

        # Create a canvas
        canvas = gtk.DrawingArea()
        canvas.set_size_request(gtk.gdk.screen_width(), \
                                gtk.gdk.screen_height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()

        self._game = Game(canvas, parent=self, path=self.path)
        self._game.new_game()

    def _setup_toolbars(self):
        """ Setup the toolbars. """

        self.max_participants = 1  # No collaboration

        toolbox = ToolbarBox()

        # Activity toolbar
        activity_button = ActivityToolbarButton(self)

        toolbox.toolbar.insert(activity_button, 0)
        activity_button.show()

        self.set_toolbar_box(toolbox)
        toolbox.show()
        self.toolbar = toolbox.toolbar

        name_game_button = radio_factory(
            'name-game',
            toolbox.toolbar,
            self._level_cb,
            cb_arg=0,
            tooltip=_(LABELS[0]),
            group=None)
        calorie_game_button = radio_factory(
            'calorie-game',
            toolbox.toolbar,
            self._level_cb,
            cb_arg=1,
            tooltip=_(LABELS[1]),
            group=name_game_button)
        pyramid_game_button = radio_factory(
            'pyramid-game',
            toolbox.toolbar,
            self._level_cb,
            cb_arg=2,
            tooltip=_(LABELS[2]),
            group=name_game_button)
        balance_game_button = radio_factory(
            'balance-game',
            toolbox.toolbar,
            self._level_cb,
            cb_arg=3,
            tooltip=_(LABELS[3]),
            group=name_game_button)

        separator_factory(toolbox.toolbar, False, True)
        self._label = label_factory(toolbox.toolbar, LABELS[0])

        separator_factory(toolbox.toolbar, True, False)
        tools_toolbar = gtk.Toolbar()
        tools_toolbar_button = ToolbarButton(
            page=tools_toolbar,
            icon_name='view-source')
        tools_toolbar.show()
        toolbox.toolbar.insert(tools_toolbar_button, -1)
        tools_toolbar_button.show()

        stop_button = StopButton(self)
        stop_button.props.accelerator = '<Ctrl>q'
        toolbox.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.name_entry = entry_factory(
            _('food name'),
            tools_toolbar,
            tooltip=_('Enter a name for the new food item.'),
            max=20)
        self.calories_entry = entry_factory(
            _('calories'),
            tools_toolbar,
            tooltip=_('Enter the calories in for the new food item.'),
            max=8)
        self.food_spinner = combo_factory(
            PYRAMID,
            tools_toolbar,
            self._food_pyramid_cb,
            default=PYRAMID[2],
            tooltip=_('Select level in the Food Pyramid.'))
        image_button = button_factory(
            'image-tools',
            tools_toolbar,
            self._load_image_cb,
            tooltip=_('Load a picture of the new food item.'))

        separator_factory(tools_toolbar, True, False)
        create_button = button_factory(
            'new-food',
            tools_toolbar,
            self._create_new_food_cb,
            tooltip=_('Add a new food item.'))

    def _level_cb(self, button, level):
        ''' Switch between levels '''
        self._game.level = level
        self._label.set_text(LABELS[level])
        self._game.new_game()

    def _food_pyramid_cb(self, button):
        return

    def _load_image_cb(self, button):
        chooser = None
        name = None
        self._new_food_image_path = None
        if hasattr(mime, 'GENERIC_TYPE_IMAGE'):
            # See SL bug #2398
            if 'image/svg+xml' not in \
                    mime.get_generic_type(mime.GENERIC_TYPE_IMAGE).mime_types:
                mime.get_generic_type(
                    mime.GENERIC_TYPE_IMAGE).mime_types.append('image/svg+xml')
            chooser = ObjectChooser(parent=self,
                                    what_filter=mime.GENERIC_TYPE_IMAGE)
        else:
            try:
                chooser = ObjectChooser(parent=self, what_filter=None)
            except TypeError:
                chooser = ObjectChooser(
                    None, self,
                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        if chooser is not None:
            try:
                result = chooser.run()
                if result == gtk.RESPONSE_ACCEPT:
                    jobject = chooser.get_selected_object()
                    if jobject and jobject.file_path:
                        name = jobject.metadata['title']
                        mime_type = jobject.metadata['mime_type']
                        _logger.debug('result of choose: %s (%s)' % \
                                          (name, str(mime_type)))
            finally:
                chooser.destroy()
                del chooser
            if name is not None:
                self._new_food_image_path = jobject.file_path
        return

    def _create_new_food_cb(self, button):

        def _notification_alert_response_cb(alert, response_id, self):
            self.remove_alert(alert)

        name = self.name_entry.get_text()
        try:
            calories = int(self.calories_entry.get_text())
        except:
            _logger.debug(self.calories_entry.get_text)
            calories = None
        pyramid = self.food_spinner.get_active()

        if name == '' or name == _('food name'):
            alert = NotifyAlert()
            alert.props.title = _('Add a new food item.')
            alert.connect('response', _notification_alert_response_cb, self)
            alert.props.msg = _('You must enter a name for the new food item.')
            self.add_alert(alert)
            alert.show()
            return
        elif calories is None or calories < 0:
            alert = NotifyAlert()
            alert.props.title = _('Add a new food item.')
            alert.connect('response', _notification_alert_response_cb, self)
            alert.props.msg = _('You must enter calories for the new food \
item.')
            self.add_alert(alert)
            alert.show()
            return
        elif self._new_food_image_path is None:
            alert = NotifyAlert()
            alert.props.title = _('Add a new food item.')
            alert.connect('response', _notification_alert_response_cb, self)
            alert.props.msg = _('You must load an image for the new food \
item.')
            self.add_alert(alert)
            alert.show()
            return

        _logger.debug(self._new_food_image_path)
        GAME_DEFS.append([name, calories, pyramid, 'apple.png'])
        self._game.word_card_append()
        self._game.picture_append(self._new_food_image_path)
        self._game.small_picture_append(self._new_food_image_path)
        alert = NotifyAlert()
        alert.props.title = _('Add a new food item.')
        alert.connect('response', _notification_alert_response_cb, self)
        alert.props.msg = _('%s has been loaded.') % (name)
        self.add_alert(alert)
        alert.show()
        self.name_entry.set_text(_('food name'))
        self.calories_entry.set_text(_('calories'))
        self._new_food_image_path = None
        self._game.new_game()
        return

    # TODO: Implement read and write file methods
