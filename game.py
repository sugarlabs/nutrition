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
_logger = logging.getLogger('nutrition-activity')

try:
    from sugar.graphics import style
    GRID_CELL_SIZE = style.GRID_CELL_SIZE
except ImportError:
    GRID_CELL_SIZE = 0

from food import FOOD_DATA, PYRAMID, NAME, CALS, GROUP, IMAGE

from sprites import Sprites, Sprite

# ChooseMyPlate.gov
MYPLATE = [[PYRAMID[0], 0], [PYRAMID[1], 1], [PYRAMID[2], 2],
           [PYRAMID[3], 2], [PYRAMID[4], 3], [PYRAMID[5], 3]]
QUANT = 1
QUANTITIES = [_('minimum'), _('moderate'), _('more'), _('most')]
BALANCE = [_('balanced'), _('unbalanced')]
NCARDS = 5
FOOD = []

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

        self._picture_cards = []
        self._small_picture_cards = []
        self._food_cards = []
        self._group_cards = []
        self._quantity_cards = []
        self._balance_cards = []
        self._background = None

        # Generate the sprites we'll need...
        self._sprites = Sprites(self._canvas)
        self._background = Sprite(
            self._sprites, 0, 0, gtk.gdk.pixbuf_new_from_file_at_size(
                os.path.join(self._path, 'images','background.png'),
                self._width, self._height))
        self._background.set_layer(0)
        self._background.type = None
        self._background.hide()

        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
            os.path.join(self._path, 'images', 'word-box.png'),
            int(350 * self._scale), int(100 * self._scale))

        for i in range(len(FOOD_DATA) / 4):
            FOOD.append([FOOD_DATA[i * 4 + NAME], FOOD_DATA[i * 4 + CALS],
                         FOOD_DATA[i * 4 + GROUP], FOOD_DATA[i * 4 + IMAGE]])
            self.picture_append(os.path.join(self._path, 'images',
                                             FOOD_DATA[i * 4 + IMAGE]))
            self.small_picture_append(os.path.join(self._path, 'images',
                                                   FOOD_DATA[i * 4 + IMAGE]))
            self.word_card_append(self._food_cards, pixbuf)
            self._food_cards[-1].type = i
            self._food_cards[-1].set_label(FOOD_DATA[i * 4 + NAME])

        x = 10
        dx, dy = self._food_cards[0].get_dimensions()

        y = 10
        for i in range(len(MYPLATE)):
            self.word_card_append(self._group_cards, pixbuf)
            self._group_cards[-1].type = i
            self._group_cards[-1].set_label(MYPLATE[i][0])
            self._group_cards[-1].move((x, y))
            y += int(dy * 1.25)

        y = 10
        for i in range(len(QUANTITIES)):
            self.word_card_append(self._quantity_cards, pixbuf)
            self._quantity_cards[-1].type = i
            self._quantity_cards[-1].set_label(QUANTITIES[i])
            self._quantity_cards[-1].move((x, y))
            y += int(dy * 1.25)

        y = 10
        for i in range(len(BALANCE)):
            self.word_card_append(self._balance_cards, pixbuf)
            self._balance_cards[-1].type = i
            self._balance_cards[-1].set_label(BALANCE[i])
            self._balance_cards[-1].move((x, y))
            y += int(dy * 1.25)

        self._smile = Sprite(self._sprites,
                             int(self._width / 4),
                             int(self._height / 4),
                             gtk.gdk.pixbuf_new_from_file_at_size(
                os.path.join(self._path, 'images', 'correct.png'),
                int(self._width / 2),
                int(self._height / 2)))
        self._smile.set_label_attributes(36)
        self._smile.set_margins(10, 0, 10, 0)

        self._frown = Sprite(self._sprites,
                             int(self._width / 4),
                             int(self._height / 4),
                             gtk.gdk.pixbuf_new_from_file_at_size(
                os.path.join(self._path, 'images', 'wrong.png'),
                int(self._width / 2),
                int(self._height / 2)))
        self._frown.set_label_attributes(36)
        self._frown.set_margins(10, 0, 10, 0)

        self.build_food_groups()

        self._all_clear()

    def word_card_append(self, card_list, pixbuf):
        card_list.append(Sprite(self._sprites, 10, 10, pixbuf))
        card_list[-1].set_label_attributes(36)
        card_list[-1].set_margins(10, 0, 10, 0)

    def picture_append(self, path):
        self._picture_cards.append(
            Sprite(self._sprites,
                   int(self._width / 2.),
                   int(self._height / 4.),
                   gtk.gdk.pixbuf_new_from_file_at_size(
                    path, int(self._width / 3.), int(9 * self._width / 12.))))
        self._picture_cards[-1].type = 'picture'

    def small_picture_append(self, path):
        x = int(self._width / 3.)
        y = int(self._height / 6.)
        for j in range(6):  # up to 6 of each card
            self._small_picture_cards.append(
                Sprite(self._sprites, x, y,
                       gtk.gdk.pixbuf_new_from_file_at_size(
                        path,
                        int(self._width / 6.),
                        int(3 * self._width / 8.))))
            self._small_picture_cards[-1].type = 'picture'
            x += int(self._width / 6.)
            if j == 2:
                x = int(self._width / 3.)
                y += int(3 * self._width / 16.)

    def _all_clear(self):
        ''' Things to reinitialize when starting up a new game. '''
        for p in self._picture_cards:
            p.hide()
        for p in self._small_picture_cards:
            p.hide()
        for i, w in enumerate(self._food_cards):
            w.set_label_color('black')
            w.set_label(FOOD[i][NAME])
            w.hide()
        for i, w in enumerate(self._group_cards):
            w.set_label_color('black')
            w.set_label(MYPLATE[i][0])
            w.hide()
        for i, w in enumerate(self._quantity_cards):
            w.set_label_color('black')
            w.set_label(QUANTITIES[i])
            w.hide()
        for i, w in enumerate(self._balance_cards):
            w.set_label_color('black')
            w.set_label(BALANCE[i])
            w.hide()
        self._smile.hide()
        self._frown.hide()

        self._background.set_layer(1)

    def build_food_groups(self):
        self._my_plate = [[], [], [], []]
        for i, food in enumerate(FOOD):
            self._my_plate[MYPLATE[food[GROUP]][QUANT]].append(i)

    def new_game(self):
        ''' Start a new game. '''
        games = {0: self._name_that_food, 1: self._name_that_food_group,
                 2: self._how_much_to_eat, 3: self._balanced_meal}
        self._all_clear()
        
        games[self.level]()
        
        self._frown.set_label('')
        self._smile.set_label('')

    def _name_that_food(self):
        ''' Choose food cards and one matching food picture '''
        x = 10
        y = 10
        dx, dy = self._food_cards[0].get_dimensions()

        # Select some cards
        word_list = []
        for i in range(NCARDS):
            j = int(uniform(0, len(FOOD)))
            while j in word_list:
                j = int(uniform(0, len(FOOD)))
            word_list.append(j)

        _logger.debug(word_list)
        # Show the word cards from the list
        for i in word_list:
            self._food_cards[i].set_layer(100)
            self._food_cards[i].move((x, y))
            y += int(dy * 1.25)

        # Choose a random food image from the list and show it.
        self._target = self._food_cards[
            word_list[int(uniform(0, NCARDS))]].type
        self._picture_cards[self._target].set_layer(100)

    def _name_that_food_group(self):
        ''' Show group cards and one food picture '''
        for i in range(len(MYPLATE)):
            self._group_cards[i].set_layer(100)

        # Choose a random food image and show it.
        self._target = int(uniform(0, len(FOOD)))
        self._picture_cards[self._target].set_layer(100)

    def _how_much_to_eat(self):
        ''' Show quantity cards and one food picture '''
        for i in range(len(QUANTITIES)):
            self._quantity_cards[i].set_layer(100)

        # Choose a random image from the list and show it.
        self._target = int(uniform(0, len(FOOD)))
        self._picture_cards[self._target].set_layer(100)

    def _balanced_meal(self):
        ''' A well-balanced meal '''
        for i in range(2):
            self._balance_cards[i].set_layer(100)

        # Determine how many foods from each group
        n = [0, 0, 0, 0]
        n[0] = int(uniform(0, 2.5))
        n[1] = int(uniform(0, 3 - n[0]))
        n[2] = 3 - n[0] - n[1]
        n[3] = 6 - n[0] - n[1] - n[2]

        _logger.debug(n)

        # Fill a plate with foods from different groups
        meal = []
        for i in range(n[0]):  # Sweets
            j = int(uniform(0, len(self._my_plate[0])))
            _logger.debug('0. %d %d' % (len(self._my_plate[0]), j))
            meal.append(self._my_plate[0][j])
        for i in range(n[1]):  # Dairy
            j = int(uniform(0, len(self._my_plate[1])))
            _logger.debug('1. %d %d' % (len(self._my_plate[1]), j))
            meal.append(self._my_plate[1][j])
        for i in range(n[2]):  # Protein and Fruits
            j = int(uniform(0, len(self._my_plate[2])))
            _logger.debug('2. %d %d' % (len(self._my_plate[2]), j))
            meal.append(self._my_plate[2][j])
        for i in range(n[3]):  # Veggies and Grains
            j = int(uniform(0, len(self._my_plate[3])))
            _logger.debug('3. %d %d' % (len(self._my_plate[3]), j))
            meal.append(self._my_plate[3][j])
        _logger.debug(meal)

        if n[0] < 2 and n[1] < 2 and n[2] < n[3]:
            self._target = 0  # Balanced meal
        else:
            self._target = 1

        # Randomly position small cards
        self._small_picture_cards[meal[3] * 6].set_layer(100)
        self._small_picture_cards[meal[4] * 6 + 1].set_layer(100)
        self._small_picture_cards[meal[1] * 6 + 2].set_layer(100)
        self._small_picture_cards[meal[2] * 6 + 3].set_layer(100)
        self._small_picture_cards[meal[5] * 6 + 4].set_layer(100)
        self._small_picture_cards[meal[0] * 6 + 5].set_layer(100)

    def _button_press_cb(self, win, event):
        win.grab_focus()
        x, y = map(int, event.get_coords())
        spr = self._sprites.find_sprite((x, y))
        if spr == None:
            return
        # We only care about clicks on word cards
        if type(spr.type) != int:
            return

        # Which card was clicked? Set its label to red.
        spr.set_label_color('red')
        label = spr.labels[0]
        spr.set_label(label)

        if self.level == 0:
            if spr.type == self._target:
                self._smile.set_layer(200)
            else:
                self._frown.set_layer(200)
            self._food_cards[self._target].set_label_color('blue')
            label = self._food_cards[self._target].labels[0]
            self._food_cards[self._target].set_label(label)
        elif self.level == 1:
            i = FOOD[self._target][GROUP]
            if spr.type == i:
                self._smile.set_layer(200)
            else:
                self._frown.set_layer(200)
            self._group_cards[i].set_label_color('blue')
            label = self._group_cards[i].labels[0]
            self._group_cards[i].set_label(label)
        elif self.level == 2:
            i = MYPLATE[FOOD[self._target][GROUP]][QUANT]
            if spr.type == i:
                self._smile.set_layer(200)
            else:
                self._frown.set_layer(200)
            self._quantity_cards[i].set_label_color('blue')
            label = self._quantity_cards[i].labels[0]
            self._quantity_cards[i].set_label(label)
        else:
            if self._target == spr.type:
                self._smile.set_layer(200)
            else:
                self._frown.set_layer(200)
            self._balance_cards[self._target].set_label_color('blue')
            label = self._balance_cards[self._target].labels[0]
            self._balance_cards[self._target].set_label(label)

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
