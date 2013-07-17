# coding=utf-8

# Utility class for reading and writing Unicode data in CSVs
# Copied and modified from the final example at
# http://docs.python.org/2/library/csv.html#examples
# Also using code form
# http://stackoverflow.com/questions/5838605/python-dictwriter-writing-utf-8-encoded-csv-files

import csv
import codecs
from StringIO import StringIO


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeDictReader(UnicodeReader):
    """
    A CSV dict reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding'
    """

    def __init__(self, f, dialect=csv.excel, encoding, **kwds):
        f = UTF8Recorder(f, encoding)
        self.reader = csv.DictReader(f, dialect=dialect, **kwds)

    @property
    def fieldnames(self):
        return self.reader.fieldnames


class UnicodeDictWriter:
    """
    A CSV DictWriter which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, fieldnames, dialect=csv.excel, encoding="utf-8",
                 **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.DictWriter(self.queue, fieldnames, dialect=dialect,
                                     **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def __encodeStream__(self):
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writeheader(self):
        self.writer.writeheader()
        self.__encodeStream__()

    def writerow(self, D):
        encoded_D = {k: unicode(v).encode("utf-8", errors="ignore") if v else
                     "" for k, v in D.items()}
        self.writer.writerow(encoded_D)
        self.__encodeStream__()

    def writerows(self, rows):
        for D in rows:
            self.writerow(D)
