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

from gi.repository import Gtk, Gdk, GObject, GdkPixbuf
import cairo
import os
from random import uniform

from gettext import gettext as _

import logging
_logger = logging.getLogger('nutrition-activity')

try:
    from sugar3.graphics import style
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

        self._canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self._canvas.connect("draw", self.__draw_cb)
        self._canvas.connect("button-press-event", self._button_press_cb)

        self._width = Gdk.Screen.width()
        self._height = Gdk.Screen.height()
        self._scale = self._width / 1200.
        self._target = 0
        self._tries = 0

        self.level = 0

        self._picture_cards = []
        self._small_picture_cards = []
        self.food_cards = []
        self._group_cards = []
        self._quantity_cards = []
        self._balance_cards = []
        self._last_twenty = []
        self._background = None

        # Generate the sprites we'll need...
        self._sprites = Sprites(self._canvas)
        self._background = Sprite(
            self._sprites, 0, 0, GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(self._path, 'images','background.png'),
                self._width, self._height))
        self._background.set_layer(0)
        self._background.type = None
        self._background.hide()

        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
            os.path.join(self._path, 'images', 'word-box.png'),
            int(350 * self._scale), int(100 * self._scale))

        for i in range(len(FOOD_DATA) / 4):
            FOOD.append([FOOD_DATA[i * 4 + NAME], FOOD_DATA[i * 4 + CALS],
                         FOOD_DATA[i * 4 + GROUP], FOOD_DATA[i * 4 + IMAGE]])
            self.food_cards.append(None)
            self._picture_cards.append(None)
            for j in range(6):
                self._small_picture_cards.append(None)
        self.allocate_food(0)

        x = 10
        dx, dy = self.food_cards[0].get_dimensions()

        y = 10
        for i in range(len(MYPLATE)):
            self.word_card_append(self._group_cards, self.pixbuf)
            self._group_cards[-1].type = i
            self._group_cards[-1].set_label(MYPLATE[i][0])
            self._group_cards[-1].move((x, y))
            y += int(dy * 1.25)

        y = 10
        for i in range(len(QUANTITIES)):
            self.word_card_append(self._quantity_cards, self.pixbuf)
            self._quantity_cards[-1].type = i
            self._quantity_cards[-1].set_label(QUANTITIES[i])
            self._quantity_cards[-1].move((x, y))
            y += int(dy * 1.25)

        y = 10
        for i in range(len(BALANCE)):
            self.word_card_append(self._balance_cards, self.pixbuf)
            self._balance_cards[-1].type = i
            self._balance_cards[-1].set_label(BALANCE[i])
            self._balance_cards[-1].move((x, y))
            y += int(dy * 1.25)

        self._smile = Sprite(self._sprites,
                             int(self._width / 4),
                             int(self._height / 4),
                             GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(self._path, 'images', 'correct.png'),
                int(self._width / 2),
                int(self._height / 2)))
        self._smile.set_label_attributes(36)
        self._smile.set_margins(10, 0, 10, 0)

        self._frown = Sprite(self._sprites,
                             int(self._width / 4),
                             int(self._height / 4),
                             GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(self._path, 'images', 'wrong.png'),
                int(self._width / 2),
                int(self._height / 2)))
        self._frown.set_label_attributes(36)
        self._frown.set_margins(10, 0, 10, 0)

        self.build_food_groups()

        self._all_clear()

    def allocate_food(self, i):
        self.picture_append(os.path.join(self._path, 'images',
                                         FOOD_DATA[i * 4 + IMAGE]), i)
        self.small_picture_append(os.path.join(self._path, 'images',
                                               FOOD_DATA[i * 4 + IMAGE]), i)
        self.word_card_append(self.food_cards, self.pixbuf, i)
        self.food_cards[i].type = i
        self.food_cards[i].set_label(FOOD_DATA[i * 4 + NAME])

    def word_card_append(self, card_list, pixbuf, i=-1):
        if i == -1:
            card_list.append(Sprite(self._sprites, 10, 10, pixbuf))
        else:
            card_list[i] = Sprite(self._sprites, 10, 10, pixbuf)
        card_list[i].set_label_attributes(36)
        card_list[i].set_margins(10, 0, 10, 0)
        card_list[i].hide()

    def picture_append(self, path, i=-1):
        spr = Sprite(
            self._sprites,
            int(self._width / 2.),
            int(self._height / 4.),
            GdkPixbuf.Pixbuf.new_from_file_at_size(
                path, int(self._width / 3.), int(9 * self._width / 12.)))
        if i == -1:
            self._picture_cards.append(spr)
        else:
            self._picture_cards[i] = spr
        self._picture_cards[i].type = 'picture'
        self._picture_cards[i].hide()

    def small_picture_append(self, path, i=-1):
        x = int(self._width / 3.)
        y = int(self._height / 6.)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
            path,
            int(self._width / 6.),
            int(3 * self._width / 8.)) 
        for j in range(6):  # up to 6 of each card
            if i == -1:
                self._small_picture_cards.append(Sprite(
                self._sprites, x, y, pixbuf))
                self._small_picture_cards[-1].type = 'picture'
                self._small_picture_cards[-1].hide()
            else:
                self._small_picture_cards[i * 6 + j] = Sprite(
                    self._sprites, x, y, pixbuf)
                self._small_picture_cards[i * 6 + j].type = 'picture'
                self._small_picture_cards[i * 6 + j].hide()
            x += int(self._width / 6.)
            if j == 2:
                x = int(self._width / 3.)
                y += int(3 * self._width / 16.)

    def _all_clear(self):
        ''' Things to reinitialize when starting up a new game. '''
        for p in self._picture_cards:
            if p is not None:
                p.hide()
        for p in self._small_picture_cards:
            if p is not None:
                p.hide()
        for i, w in enumerate(self.food_cards):
            if w is not None:
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
                 2: self._compare_calories, 3: self._how_much_to_eat,
                 4: self._balanced_meal}
        self._all_clear()
        
        games[self.level]()
        
        self._frown.set_label('')
        self._smile.set_label('')
        self._tries = 0

    def _name_that_food(self):
        ''' Choose food cards and one matching food picture '''
        x = 10
        y = 10
        dx, dy = self.food_cards[0].get_dimensions()

        # Select some cards
        word_list = []
        for i in range(NCARDS):
            j = int(uniform(0, len(FOOD)))
            while j in word_list:
                j = int(uniform(0, len(FOOD)))
            word_list.append(j)

        # Show the word cards from the list
        for i in word_list:
            if self.food_cards[i] is None:
                self.allocate_food(i)
            self.food_cards[i].set_layer(100)
            self.food_cards[i].move((x, y))
            y += int(dy * 1.25)

        # Choose a random food image from the list and show it.
        self._target = self.food_cards[
            word_list[int(uniform(0, NCARDS))]].type
        while self._target in self._last_twenty:
            self._target = self.food_cards[
                word_list[int(uniform(0, NCARDS))]].type
        self._last_twenty.append(self._target)
        if len(self._last_twenty) > 20:
            self._last_twenty.remove(self._last_twenty[0])
            
        self._picture_cards[self._target].set_layer(100)

    def _name_that_food_group(self):
        ''' Show group cards and one food picture '''
        for i in range(len(MYPLATE)):
            self._group_cards[i].set_layer(100)

        # Choose a random food image and show it.
        self._target = int(uniform(0, len(FOOD)))
        if self.food_cards[self._target] is None:
            self.allocate_food(self._target)
        self._picture_cards[self._target].set_layer(100)

    def _compare_calories(self):
        ''' Choose food cards and compare the calories '''
        x = 10
        y = 10
        dx, dy = self.food_cards[0].get_dimensions()

        # Select some cards
        word_list = []
        for i in range(6):
            j = int(uniform(0, len(FOOD)))
            while j in word_list:
                j = int(uniform(0, len(FOOD)))
            word_list.append(j)
            if self.food_cards[j] is None:
                self.allocate_food(j)

        # Show the word cards from the list
        for i in word_list:
            self.food_cards[i].set_layer(100)
            self.food_cards[i].move((x, y))
            y += int(dy * 1.25)

        # Show food images
        self._target = word_list[0]
        for i in range(5):
             if FOOD[word_list[i + 1]][CALS] > FOOD[self._target][CALS]:
                 self._target = word_list[i + 1]
        self._small_picture_cards[word_list[0] * 6].set_layer(100)
        self._small_picture_cards[word_list[1] * 6 + 1].set_layer(100)
        self._small_picture_cards[word_list[2] * 6 + 2].set_layer(100)
        self._small_picture_cards[word_list[3] * 6 + 3].set_layer(100)
        self._small_picture_cards[word_list[4] * 6 + 4].set_layer(100)
        self._small_picture_cards[word_list[5] * 6 + 5].set_layer(100)

    def _how_much_to_eat(self):
        ''' Show quantity cards and one food picture '''
        for i in range(len(QUANTITIES)):
            self._quantity_cards[i].set_layer(100)

        # Choose a random image from the list and show it.
        self._target = int(uniform(0, len(FOOD)))
        if self.food_cards[self._target] is None:
            self.allocate_food(self._target)
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

        # Fill a plate with foods from different groups
        meal = []
        for i in range(n[0]):  # Sweets
            j = int(uniform(0, len(self._my_plate[0])))
            meal.append(self._my_plate[0][j])
        for i in range(n[1]):  # Dairy
            j = int(uniform(0, len(self._my_plate[1])))
            meal.append(self._my_plate[1][j])
        for i in range(n[2]):  # Protein and Fruits
            j = int(uniform(0, len(self._my_plate[2])))
            meal.append(self._my_plate[2][j])
        for i in range(n[3]):  # Veggies and Grains
            j = int(uniform(0, len(self._my_plate[3])))
            meal.append(self._my_plate[3][j])

        if n[0] < 2 and n[1] < 2 and n[2] < n[3]:
            self._target = 0  # Balanced meal
        else:
            self._target = 1

        for i in range(6):
            if self.food_cards[meal[i]] is None:
                self.allocate_food(meal[i])
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
                self._tries = 3
            else:
                self._frown.set_layer(200)
                self._tries += 1
            if self._tries == 3:
                self.food_cards[self._target].set_label_color('blue')
                label = self.food_cards[self._target].labels[0]
                self.food_cards[self._target].set_label(label)
        elif self.level == 1:
            i = FOOD[self._target][GROUP]
            if spr.type == i:
                self._smile.set_layer(200)
                self._tries = 3
            else:
                self._frown.set_layer(200)
                self._tries += 1
            if self._tries == 3:
                self._group_cards[i].set_label_color('blue')
                label = self._group_cards[i].labels[0]
                self._group_cards[i].set_label(label)
        elif self.level == 2:
            if spr.type == self._target:
                self._smile.set_layer(200)
                self._tries = 3
            else:
                self._frown.set_layer(200)
                self._tries += 1
            if self._tries == 3:
                self.food_cards[self._target].set_label_color('blue')
                label = self.food_cards[self._target].labels[0]
                self.food_cards[self._target].set_label(label)
        elif self.level == 3:
            i = MYPLATE[FOOD[self._target][GROUP]][QUANT]
            if spr.type == i:
                self._smile.set_layer(200)
                self._tries = 3
            else:
                self._frown.set_layer(200)
                self._tries += 1
            if self._tries == 3:
                self._quantity_cards[i].set_label_color('blue')
                label = self._quantity_cards[i].labels[0]
                self._quantity_cards[i].set_label(label)
        elif self.level == 4:
            if self._target == spr.type:
                self._smile.set_layer(200)
                self._tries = 3
            else:
                self._frown.set_layer(200)
                self._tries += 1
            if self._tries == 3:
                self._balance_cards[self._target].set_label_color('blue')
                label = self._balance_cards[self._target].labels[0]
                self._balance_cards[self._target].set_label(label)
        else:
            _logger.debug('unknown play level %d' % (self.level))

        # Play again
        if self._tries == 3:
            GObject.timeout_add(2000, self.new_game)
        else:
            GObject.timeout_add(1000, self._reset_game)
        return True

    def _reset_game(self):
        self._frown.hide()
        if self.level in [0, 2]:
            for i, w in enumerate(self.food_cards):
                w.set_label_color('black')
                w.set_label(FOOD[i][NAME])
        elif self.level == 1:
            for i, w in enumerate(self._group_cards):
                w.set_label_color('black')
                w.set_label(MYPLATE[i][0])
        elif self.level == 3:
            for i, w in enumerate(self._quantity_cards):
                w.set_label_color('black')
                w.set_label(QUANTITIES[i])
        elif self.level == 4:
            for i, w in enumerate(self._balance_cards):
                w.set_label_color('black')
                w.set_label(BALANCE[i])

    def __draw_cb(self, canvas, cr):
        self._sprites.redraw_sprites(cr=cr)

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
        Gtk.main_quit()
