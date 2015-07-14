#!/usr/bin/env python
"""verdict.py docstring
Turn the spreadsheet into a flatfile.
"""
import os
import sys
import json
import doctest
import csv
import codecs, cStringIO
from datetime import date, datetime, timedelta
import time
import gspread
import math
from spreadsheet import Sheet
from collections import defaultdict, OrderedDict
import argparse


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class Verdict:
    """ Handle the spreadsheet-specific parts of publishing
        from Google Sheets.
        """

    def __init__(self, sheet):
        self.sheet = sheet
        self.is_metro = False

    def publish(self, worksheet=None):
        """ Publish the verdict data in whatever permutations we need.
            This assumes the spreadsheet's key names are in the first row.
            >>> sheet = Sheet('test-sheet', 'worksheet-name')
            >>> verdict = Verdict(sheet)
            >>> verdict.publish()
            True
            """
        if not self.sheet.sheet or worksheet:
            self.sheet.sheet = self.open_worksheet(worksheet)

        if not worksheet:
            worksheet = self.sheet.worksheet

        self.sheet.build_filename()

        rows = self.sheet.sheet.get_all_values()
        keys = rows[0]
        fn = {
            'json': open('%s/output/%s.json' % (self.sheet.directory, self.sheet.filename), 'wb'),
            'jsonp': open('%s/output/%s.jsonp' % (self.sheet.directory, self.sheet.filename), 'wb'),
            'csv': open('%s/output/%s.csv' % (self.sheet.directory, self.sheet.filename), 'wb')
        }
        recordwriter = UnicodeWriter(fn['csv'], delimiter=',', 
                                     quotechar='"', quoting=csv.QUOTE_MINIMAL)
        records = []
        for i, row in enumerate(rows):
            if i == 0:
                keys = row
                recordwriter.writerow(keys)
                continue
            record = dict(zip(keys, row))
            # {'Bad Thing': 'Test two', 'Timestamp': '5/27/2015 17:01:39', 'URL': '', 'Value': '7', 'Date': '5/26/2015'}

            # We write lines one-by-one. If we have filters, we run
            # through them here to see if we're handling a record we
            # shouldn't be writing.
            publish = True
            if self.sheet.filters:
                for item in self.sheet.filters:
                    # Special handling for filtering by years. Hard-coded.
                    if item['key'] == 'Year':
                        if item['value'] not in record['Date']:
                            publish = False
                    elif record[item['key']] != item['value']:
                        publish = False

            if publish:
                # Turn the date into a timestamp.
                try:
                    timestamp = record['Timestamp'].split(' ')[0]
                    record['Timestamp'] = timestamp
                    if record['Date'] == '':
                        # We do this so we can use the Date field from here on out.
                        record['Date'] = record['Timestamp']
                    else:
                        timestamp = record['Date']
                    day = datetime.strptime(timestamp, "%m/%d/%Y")
                    record['unixtime'] = int(time.mktime(day.timetuple()))
                except:
                    record['unixtime'] = 0

                # We want to know how many days ago this happened,
                # and add that to the record.
                days_ago = datetime.today() - day
                record['ago'] = days_ago.days
                
                recordwriter.writerow(row)
                records += [record]

        # Now build the day-by-day Verdict Indexes.
        # We'll have a list of date/value pairs by the end of this.
        items = []
        for record in records:
            items.append((record['Date'], record['Value']))
        self.items = items
        scores = self.calc_score()
        if scores:
            fh = open('output/scores.json', 'wb')
            json.dump(scores, fh)
            fh.close()
            content = json.dumps(scores)
            fh = open('output/scores.jsonp', 'wb')
            fh.write('verdict_scores_callback(%s);' % content)
            fh.close()
            

        if records:
            json.dump(records, fn['json'])
            content = json.dumps(records)
            fn['jsonp'].write('verdict_callback(%s);' % content)

        return True

    def calc_score(self):
        """ Given a dict of date/score tuples, return a per-day list of date/score tuples.
            We use an OrderedDict so we know what the first day of events is --
            we can't be certain that something happens on every day, so we use
            the first-day to populate a dict with every date between then and now.

            Keep in mind more than one event can happen per day.
            Also keep in mind that an event on one day still affects the 
            next day's score -- it's worth half what it was worth the day before.
            """
        # items is expected to look something like
        # [('6/1/2015', '2'), ('6/2/2015', '10'), ('6/3/2015', '4')]

        # Consolidate the dates so we can make a set with this object.
        event_days = OrderedDict()
        distinct_days = OrderedDict()
        for item in self.items:
            if item[0] not in event_days:
                event_days[item[0]] = 0
        first_day = datetime.strptime(next(iter(event_days)), "%m/%d/%Y").date()
        today = date.today()

        i = 0
        while True:
            day = first_day + timedelta(days=i)
            day_str = date.strftime(day, "%-m/%-d/%Y")
            distinct_days[day_str] = 0
            i += 1
            if day == today:
                break

        # Add up the raw score.
        for item in self.items:
            distinct_days[item[0]] += int(item[1])

        # Now loop through the raw score, and calculate the total scores.
        # The next day's score is equal to half of the previous day's score plus any new events.
        previous_score = 0
        for day in iter(distinct_days):
            score = round(previous_score/float(2.1)) + distinct_days[day]
            distinct_days[day] = score
            previous_score = score

        return distinct_days

def main(args):
    """ 
        """
    sheet = Sheet('Verdict', 'numeric')
    sheet.set_options(args)
    verdict = Verdict(sheet)
    verdict.publish()

def build_parser(args):
    """ A method to handle argparse.
        """
    parser = argparse.ArgumentParser(usage='$ python verdict.py',
                                     description='''Downloads, filters and 
                                                    re-publishes the Google
                                                    sheet.''',
                                     epilog='')
    parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true")
    return parser.parse_args()

if __name__ == '__main__':
    args = build_parser(sys.argv)

    if args.verbose:
        doctest.testmod(verbose=args.verbose)

    main(args)
