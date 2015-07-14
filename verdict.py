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


            # If it's the config sheet:
            if 'sheet' in record:
                recordwriter.writerow(row)
                records += [record]
                continue

            # numeric looks like:
            # {"Charge": "Attempted murder in the first degree, after deliberation and with intent", "Verdict": "", "Count No.": "31", "name_full": "Alejandra Cardona-Lamas"}
            # by-victim looks like
            # {"Verdict": "", "Charge": "Attempted murder in the first degree, with \"universal malice manifesting extreme indifference\"", "name_first": "Kaylan", "Count No.": "", "name_last": "Bailey"}

            # We need both name_full and name_last
            if 'name_full' in record:
                record['name_last'] = record['name_full'].split(' ')[-1]
            else:
                record['name_full'] = '%s %s' % (record['name_first'], record['name_last'])

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
                # We filter field values here.

                recordwriter.writerow(row)
                records += [record]

        """
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
        """ 

        if records:
            json.dump(records, fn['json'])
            content = json.dumps(records)
            fn['jsonp'].write('verdict_callback(%s);' % content)

        return True

def main(args):
    """ 
        """
    sheet = Sheet('Verdict', 'config')
    sheet.set_options(args)
    verdict = Verdict(sheet)
    verdict.publish()
    sheet = Sheet('Verdict', 'numeric')
    sheet.set_options(args)
    verdict = Verdict(sheet)
    verdict.publish()
    sheet = Sheet('Verdict', 'by-victim')
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
