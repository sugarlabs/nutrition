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
from sugar.activity.widgets import StopButton

from gettext import gettext as _

from game import Game
from toolbar_utils import separator_factory, radio_factory, label_factory

import logging
_logger = logging.getLogger('nutrition-activity')


SERVICE = 'org.sugarlabs.NutritionActivity'
IFACE = SERVICE
LABELS = [_('Match the food to its name.'),
          _('How many calories are there?'),
          _('How much should you eat?'),
          _('Is this a well-balanced meal?')]


class NutritionActivity(activity.Activity):
    """ Simple nutrition game based on GCompris ImageID """

    def __init__(self, handle):
        """ Initialize the toolbars and the game board """
        super(NutritionActivity, self).__init__(handle)

        self.path = activity.get_bundle_path()

        self._setup_toolbars()

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
        stop_button = StopButton(self)
        stop_button.props.accelerator = '<Ctrl>q'
        toolbox.toolbar.insert(stop_button, -1)
        stop_button.show()

    def _level_cb(self, button, level):
        ''' Switch between levels '''
        self._game.level = level
        self._label.set_text(LABELS[level])
        self._game.new_game()
