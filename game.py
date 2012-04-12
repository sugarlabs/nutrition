# -*- coding: utf-8 -*-
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
import gobject
import cairo
import os
from random import uniform

from gettext import gettext as _

import logging
_logger = logging.getLogger('imageid-activity')

try:
    from sugar.graphics import style
    GRID_CELL_SIZE = style.GRID_CELL_SIZE
except ImportError:
    GRID_CELL_SIZE = 0

from sprites import Sprites, Sprite

# Food Pyramid
LEVELS = [_('minimum'), _('moderate'), _('most'), _('unlimited')]
# Food name; calories; food pyramid level, image file name
GAME_DEFS = [[_('banana'), 105, 2, 'banana.png'],
             [_('apple'), 72, 2, 'apple.png'],
             [_('fish'), 58, 1, 'fish.png'],
             [_('corn'), 96, 2, 'corn.png'],
             [_('broccoli'), 55, 2, 'broccoli.png'],
             [_('chicken'), 262, 1, 'chicken.png'],
             [_('cheese'), 114, 1, 'cheese.png'],
             [_('orange'), 62, 2, 'orange.png'],
             [_('potato'), 159, 2, 'potato.png'],
             [_('water'), 0, 3, 'water.png'],
             [_('tomato'), 150, 2, 'tomato.png'],
             [_('cookie'), 68, 0, 'cookie.png'],
             [_('beef'), 284, 1, 'beef.png'],
             [_('egg'), 77, 1, 'egg.png'],
             [_('sweetpotato'), 169, 2, 'sweetpotato.png'],
             [_('tamale'), 126, 2, 'nacatamal.png'],
             [_('bread'), 69, 2, 'bread.png'],
             [_('rice and beans'), 411, 2, 'rice-and-beans.png'],
             [_('cake'), 387, 0, 'cake.png']]
GAME4 = [_('balanced'), _('unbalanced')]
NCARDS = 4

class Game():

    def __init__(self, canvas, parent=None, path=None):
        self._canvas = canvas
        self._parent = parent
        self._parent.show_all()
        self._path = path

        self._canvas.set_flags(gtk.CAN_FOCUS)
        self._canvas.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self._canvas.connect("expose-event", self._expose_cb)
        self._canvas.connect("button-press-event", self._button_press_cb)

        self._width = gtk.gdk.screen_width()
        self._height = gtk.gdk.screen_height()
        self._scale = self._width / 1200.
        self._target = 0

        self.level = 0

        # Fill the Food Pyramid
        self._food_pyramid = [[], [], [], []]
        for i, f in enumerate(GAME_DEFS):
            self._food_pyramid[f[2]].append(i)

        # Generate the sprites we'll need...
        self._sprites = Sprites(self._canvas)
        self._backgrounds = []
        for i in range(4):  # One background for each level
            self._backgrounds.append(Sprite(
                    self._sprites, 0, 0, gtk.gdk.pixbuf_new_from_file_at_size(
                        os.path.join(self._path, 'images',
                                     'background%d.png' % (i)),
                        self._width, self._height)))
            self._backgrounds[-1].set_layer(0)
            self._backgrounds[-1].type = 'background'
            self._backgrounds[-1].hide()

        self._picture_cards = []
        for i in GAME_DEFS:
            self._picture_cards.append(
                Sprite(self._sprites,
                       int(self._width / 2.),
                       int(self._height / 4.),
                       gtk.gdk.pixbuf_new_from_file_at_size(
                        os.path.join(self._path, 'images', i[-1]),
                        int(self._width / 3.),
                        int(9 * self._width / 12.))))
            self._picture_cards[-1].type = 'picture'

        self._small_picture_cards = []
        for i in GAME_DEFS:
            x = int(self._width / 3.)
            y = int(self._height / 6.)
            for j in range(6):  # up to 6 of each card
                self._small_picture_cards.append(
                    Sprite(self._sprites, x, y,
                           gtk.gdk.pixbuf_new_from_file_at_size(
                            os.path.join(self._path, 'images', i[-1]),
                            int(self._width / 6.),
                            int(3 * self._width / 8.))))
                self._small_picture_cards[-1].type = 'picture'
                x += int(self._width / 6.)
                if j == 2:
                    x = int(self._width / 3.)
                    y += int(3 * self._width / 16.)

        self._word_cards = []
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
            os.path.join(self._path, 'images', 'word-box.png'),
            int(350 * self._scale), int(100 * self._scale))
        for i in GAME_DEFS:
            self._word_cards.append(Sprite(self._sprites, 10, 10, pixbuf))
            self._word_cards[-1].set_label_attributes(36)
            self._word_cards[-1].type = 'word'

        self._smile = Sprite(self._sprites,
                             int(self._width / 4),
                             int(self._height / 4),
                             gtk.gdk.pixbuf_new_from_file_at_size(
                os.path.join(self._path, 'images', 'smiley_good.png'),
                int(self._width / 2),
                int(self._height / 2)))
        self._smile.set_label_attributes(36)

        self._frown = Sprite(self._sprites,
                             int(self._width / 4),
                             int(self._height / 4),
                             gtk.gdk.pixbuf_new_from_file_at_size(
                os.path.join(self._path, 'images', 'smiley_bad.png'),
                int(self._width / 2),
                int(self._height / 2)))
        self._frown.set_label_attributes(36)

        self._all_clear()

    def _all_clear(self):
        ''' Things to reinitialize when starting up a new game. '''
        for p in self._picture_cards:
            p.hide()
        for p in self._small_picture_cards:
            p.hide()
        for i, w in enumerate(self._word_cards):
            w.set_label_color('black')
            if self.level in [0, 1]:
                w.set_label(GAME_DEFS[i][self.level])
            else:
                w.set_label('')
            w.hide()
        self._smile.hide()
        self._frown.hide()

        self._backgrounds[self.level].set_layer(1)

    def new_game(self):
        ''' Start a new game. '''
        self._all_clear()
        if self.level in [0, 1, 2]:
            self._games_123()
        else:
            self._games_4()

    def _games_123(self):
        x = 10  # some small offset from the left edge
        y = 10  # some small offset from the top edge
        dx, dy = self._word_cards[0].get_dimensions()

        # Select N cards
        self._list = []
        for i in range(NCARDS):
            j = int(uniform(0, len(GAME_DEFS)))
            while j in self._list:
                j = int(uniform(0, len(GAME_DEFS)))
            self._list.append(j)

        # Show the word cards from the list
        j = 0
        for i in self._list:
            self._word_cards[i].set_layer(100)
            self._word_cards[i].move((x, y))
            if self.level == 2:
                self._word_cards[i].set_label(LEVELS[j])
            y += int(dy * 1.25)
            j += 1

        # Choose a random image from the list and show it.
        self._target = int(uniform(0, NCARDS))
        self._picture_cards[self._list[self._target]].set_layer(100)

    def _games_4(self):
        x = 10  # some small offset from the left edge
        y = 10  # some small offset from the top edge
        dx, dy = self._word_cards[0].get_dimensions()

        # Show two word cards
        for i in range(2):
            self._word_cards[i].set_layer(100)
            self._word_cards[i].move((x, y))
            self._word_cards[i].set_label(GAME4[i])
            y += int(dy * 1.25)

        n = [0, 0, 0]
        n[0] = int(uniform(0, 5))
        n[1] = int(uniform(0, 6 - n[0]))
        n[2] = 6 - n[0] - n[1]
        self._list = []
        for i in range(n[0]):  # Sweets
            self._list.append(self._food_pyramid[0][
                    int(uniform(0, len(self._food_pyramid[0])))])
        for i in range(n[1]):  # Meats and dairy
            self._list.append(self._food_pyramid[1][
                    int(uniform(0, len(self._food_pyramid[1])))])
        for i in range(n[2]):  # Veggies and fruits
            self._list.append(self._food_pyramid[2][
                    int(uniform(0, len(self._food_pyramid[2])))])

        if n[0] < n[1] and n[1] < n[2]:  # Balanced meal
            self._target = True
        else:
            self._target = False

        # Randomly position small cards
        self._small_picture_cards[self._list[3] * 6].set_layer(100)
        self._small_picture_cards[self._list[4] * 6 + 1].set_layer(100)
        self._small_picture_cards[self._list[1] * 6 + 2].set_layer(100)
        self._small_picture_cards[self._list[2] * 6 + 3].set_layer(100)
        self._small_picture_cards[self._list[5] * 6 + 4].set_layer(100)
        self._small_picture_cards[self._list[0] * 6 + 5].set_layer(100)

    def _button_press_cb(self, win, event):
        win.grab_focus()
        x, y = map(int, event.get_coords())
        spr = self._sprites.find_sprite((x, y))
        if spr == None:
            return
        if spr.type != 'word':  # We only care about clicks on word cards
            return

        # Which card was clicked? Set its label to red.
        i = self._word_cards.index(spr)
        self._word_cards[i].set_label_color('red')
        if self.level in [0, 1]:
            self._word_cards[i].set_label(GAME_DEFS[i][self.level])
        elif self.level == 2:
            j = self._list.index(i)
            self._word_cards[i].set_label(LEVELS[j])
        else:
            self._word_cards[i].set_label(GAME4[i])

        # If the label matches the picture, smile
        if self.level in [0, 1]:
            if i == self._list[self._target]:
                self._smile.set_layer(200)
                if self.level == 0:
                    self._smile.set_label('%d calories' % (
                            GAME_DEFS[self._list[self._target]][1]))
            else:
                self._frown.set_layer(200)
                self._frown.set_label(
                    GAME_DEFS[self._list[self._target]][self.level])
        elif self.level == 2:
            if j == GAME_DEFS[self._list[self._target]][2]:
                self._smile.set_layer(200)
            else:
                self._frown.set_layer(200)
                self._frown.set_label(
                    LEVELS[GAME_DEFS[self._list[self._target]][2]])
        else:
            _logger.debug('%s, %d' % (str(self._target), i))
            if self._target and i == 0:
                self._smile.set_layer(200)
            elif not self._target and i == 1:
                self._smile.set_layer(200)
            else:
                self._frown.set_layer(200)

        # Play again
        gobject.timeout_add(2000, self.new_game)
        return True

    def _expose_cb(self, win, event):
        self.do_expose_event(event)

    def do_expose_event(self, event):
        ''' Handle the expose-event by drawing '''
        # Restrict Cairo to the exposed area
        cr = self._canvas.window.cairo_create()
        cr.rectangle(event.area.x, event.area.y,
                event.area.width, event.area.height)
        cr.clip()
        # Refresh sprite list
        self._sprites.redraw_sprites(cr=cr)

    def _destroy_cb(self, win, event):
        gtk.main_quit()
