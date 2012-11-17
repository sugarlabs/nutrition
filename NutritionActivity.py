# -*- coding: utf-8 -*-
# Copyright (c) 2011,12 Walter Bender
# Ported to GTK3: 
# Ignacio Rodríguez <ignaciorodriguez@sugarlabs.org>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA

from gi.repository import Gtk, Gdk
from sugar3.activity import activity
from sugar3 import profile
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics.objectchooser import ObjectChooser
from sugar3.datastore import datastore
from sugar3 import mime

from gettext import gettext as _

from game import Game, FOOD
from food import PYRAMID
from toolbar_utils import separator_factory, radio_factory, label_factory, \
    button_factory, entry_factory, combo_factory

import logging
_logger = logging.getLogger('nutrition-activity')


SERVICE = 'org.sugarlabs.NutritionActivity'
IFACE = SERVICE
LABELS = [_('Match the food to its name.'),
          _('What is the food group?'),
          _('Which has the most calories?'),
          _('How much should you eat?'),
          _('Is this a well-balanced meal?')]

class NutritionActivity(activity.Activity):
    """ Simple nutrition game based on GCompris ImageID """

    def __init__(self, handle):
        """ Initialize the toolbars and the game board """
        super(NutritionActivity, self).__init__(handle)

        self.path = activity.get_bundle_path()

        self._setup_toolbars()
        self._custom_food_jobject = None
        self._custom_food_counter = 0

        # Create a canvas
        canvas = Gtk.DrawingArea()
        canvas.set_size_request(Gdk.Screen.width(), \
                                Gdk.Screen.height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()

        self._game = Game(canvas, parent=self, path=self.path)

        if 'counter' in self.metadata:
            self._custom_food_counter = int(self.metadata['counter'])
            _logger.debug(self._custom_food_counter)
            for i in range(self._custom_food_counter):
                try:
                    name = self.metadata['name-%d' % (i)]
                    _logger.debug(name)
                    calories = int(self.metadata['calories-%d' % (i)])
                    pyramid = int(self.metadata['pyramid-%d' % (i)])
                    jobject = datastore.get(self.metadata['jobject-%d' % (i)])
                    _logger.debug(jobject.file_path)
                    FOOD.append([name, calories, pyramid, 'apple.png'])
                    self._game.word_card_append(self._game.food_cards,
                                                self._game.pixbuf)
                    self._game.food_cards[-1].type = len(FOOD) - 1
                    self._game.food_cards[-1].set_label(name)
                    self._game.picture_append(jobject.file_path)
                    self._game.small_picture_append(jobject.file_path)
                except:
                    _logger.debug('Could not reload saved food item %d' % (i))
            self._game.build_food_groups()
        else:
            _logger.debug('Counter not found in metadata.')
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
        group_game_button = radio_factory(
            'group-game',
            toolbox.toolbar,
            self._level_cb,
            cb_arg=1,
            tooltip=_(LABELS[1]),
            group=name_game_button)
        calorie_game_button = radio_factory(
            'calorie-game',
            toolbox.toolbar,
            self._level_cb,
            cb_arg=2,
            tooltip=_(LABELS[2]),
            group=name_game_button)
        pyramid_game_button = radio_factory(
            'pyramid-game',
            toolbox.toolbar,
            self._level_cb,
            cb_arg=3,
            tooltip=_(LABELS[3]),
            group=name_game_button)
        balance_game_button = radio_factory(
            'balance-game',
            toolbox.toolbar,
            self._level_cb,
            cb_arg=4,
            tooltip=_(LABELS[4]),
            group=name_game_button)

        separator_factory(toolbox.toolbar, False, True)
        self._label = label_factory(toolbox.toolbar, LABELS[0], width=150)

        separator_factory(toolbox.toolbar, True, False)
        tools_toolbar = Gtk.Toolbar()
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
            self._create_custom_food_cb,
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
        self._custom_food_jobject = None
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
                    Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)
        if chooser is not None:
            try:
                result = chooser.run()
                if result == Gtk.ResponseType.ACCEPT:
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
                self._custom_food_jobject = jobject
        return

    def _create_custom_food_cb(self, button):

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
        elif self._custom_food_jobject is None:
            alert = NotifyAlert()
            alert.props.title = _('Add a new food item.')
            alert.connect('response', _notification_alert_response_cb, self)
            alert.props.msg = _('You must load an image for the new food \
item.')
            self.add_alert(alert)
            alert.show()
            return

        _logger.debug(self._custom_food_jobject.file_path)
        FOOD.append([name, calories, pyramid, 'apple.png'])
        self._game.word_card_append(self._game.food_cards,
                                    self._game.pixbuf)
        self._game.food_cards[-1].type = len(FOOD) - 1
        self._game.food_cards[-1].set_label(name)
        self._game.picture_append(self._custom_food_jobject.file_path)
        self._game.small_picture_append(self._custom_food_jobject.file_path)
        alert = NotifyAlert()
        alert.props.title = _('Add a new food item.')
        alert.connect('response', _notification_alert_response_cb, self)
        alert.props.msg = _('%s has been loaded.') % (name)
        self.add_alert(alert)
        alert.show()
        self.name_entry.set_text(_('food name'))
        self.calories_entry.set_text(_('calories'))
        self._custom_food_image_path = None
        self._game.build_food_groups()
        self._game.new_game()
        self.metadata['name-%d' % (self._custom_food_counter)] = name
        self.metadata['calories-%d' % (self._custom_food_counter)] = \
            str(calories)
        self.metadata['pyramid-%d' % (self._custom_food_counter)] = str(pyramid)
        self.metadata['jobject-%d' % (self._custom_food_counter)] = \
            self._custom_food_jobject.object_id
        self._custom_food_counter += 1
        _logger.debug('writing %d to counter' % (self._custom_food_counter))
        self.metadata['counter'] = str(self._custom_food_counter)
        return
