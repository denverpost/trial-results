#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest
from spreadsheet import Sheet
from verdict import Verdict

def test_publish():
    """ Test publish method.
        """
    sheet = Sheet('test-sheet', 'worksheet-name')
    publish = Verdict(sheet)
    publish_value = publish.publish()
    assert publish_value == True
