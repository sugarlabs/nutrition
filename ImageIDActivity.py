#Copyright (c) 2011 Walter Bender

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
try:
    from sugar.graphics.toolbarbox import ToolbarBox
    _have_toolbox = True
except ImportError:
    _have_toolbox = False

if _have_toolbox:
    from sugar.activity.widgets import ActivityToolbarButton
    from sugar.activity.widgets import StopButton

from gettext import gettext as _

from game import Game
from toolbar_utils import separator_factory

import logging
_logger = logging.getLogger('imageid-activity')


SERVICE = 'org.sugarlabs.ImageIDActivity'
IFACE = SERVICE


class ImageIDActivity(activity.Activity):
    """ Simple reading game based on GCompris ImageID """

    def __init__(self, handle):
        """ Initialize the toolbars and the game board """
        super(ImageIDActivity, self).__init__(handle)

        self.path = activity.get_bundle_path()

        self._setup_toolbars(_have_toolbox)

        # Create a canvas
        canvas = gtk.DrawingArea()
        canvas.set_size_request(gtk.gdk.screen_width(), \
                                gtk.gdk.screen_height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()

        self._game = Game(canvas, parent=self, path=self.path)
        self._game.new_game()

    def _setup_toolbars(self, have_toolbox):
        """ Setup the toolbars. """

        self.max_participants = 1  # No collaboration

        if have_toolbox:
            toolbox = ToolbarBox()

            # Activity toolbar
            activity_button = ActivityToolbarButton(self)

            toolbox.toolbar.insert(activity_button, 0)
            activity_button.show()

            self.set_toolbar_box(toolbox)
            toolbox.show()
            self.toolbar = toolbox.toolbar

        else:
            # Use pre-0.86 toolbar design
            games_toolbar = gtk.Toolbar()
            toolbox = activity.ActivityToolbox(self)
            self.set_toolbox(toolbox)
            toolbox.add_toolbar(_('Game'), games_toolbar)
            toolbox.show()
            toolbox.set_current_toolbar(1)
            self.toolbar = games_toolbar

        if _have_toolbox:
            separator_factory(toolbox.toolbar, True, False)
            stop_button = StopButton(self)
            stop_button.props.accelerator = '<Ctrl>q'
            toolbox.toolbar.insert(stop_button, -1)
            stop_button.show()
