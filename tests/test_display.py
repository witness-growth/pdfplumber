#!/usr/bin/env python
import unittest
import pdfplumber
import os
import io

import logging

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        self.pdf = pdfplumber.open(path)
        self.im = self.pdf.pages[0].to_image()

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_basic_conversion(self):
        self.im.reset()
        self.im.draw_rects(self.im.page.rects)
        self.im.draw_circle(self.im.page.chars[0])
        self.im.draw_line(self.im.page.edges[0])
        self.im.draw_vlines([10])
        self.im.draw_hlines([10])

    def test_debug_tablefinder(self):
        self.im.reset()
        settings = {"horizontal_strategy": "text", "intersection_tolerance": 5}
        self.im.debug_tablefinder(settings)

    def test_bytes_stream_to_image(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        page = pdfplumber.PDF(io.BytesIO(open(path, "rb").read())).pages[0]
        page.to_image()

    def test_curves(self):
        path = os.path.join(HERE, "../examples/pdfs/ag-energy-round-up-2017-02-24.pdf")
        page = pdfplumber.open(path).pages[0]
        im = page.to_image()
        im.draw_lines(page.curves)

    def test_cropped(self):
        im = self.pdf.pages[0].crop((10, 20, 30, 50)).to_image()
        assert im.original.size == (20, 30)

    def test_copy(self):
        assert self.im.copy().original == self.im.original
