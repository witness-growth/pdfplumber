#!/usr/bin/env python
import unittest
import pytest
import pdfplumber
from pdfplumber import utils
from pdfminer.pdfparser import PDFObjRef
from pdfminer.psparser import PSLiteral
from itertools import groupby
from operator import itemgetter
import os

import logging

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/pdffill-demo.pdf")
        self.pdf = pdfplumber.open(path)

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_cluster_list(self):
        a = [1, 2, 3, 4]
        assert utils.cluster_list(a) == [[x] for x in a]
        assert utils.cluster_list(a, tolerance=1) == [a]

        a = [1, 2, 5, 6]
        assert utils.cluster_list(a, tolerance=1) == [[1, 2], [5, 6]]

    def test_cluster_objects(self):
        a = ["a", "ab", "abc", "b"]
        assert utils.cluster_objects(a, len, 0) == [["a", "b"], ["ab"], ["abc"]]

    def test_resolve(self):
        annot = self.pdf.annots[0]
        annot_ad0 = utils.resolve(annot["data"]["A"]["D"][0])
        assert annot_ad0["MediaBox"] == [0, 0, 612, 792]
        assert utils.resolve(1) == 1

    def test_resolve_all(self):
        info = self.pdf.doc.xrefs[0].trailer["Info"]
        assert type(info) == PDFObjRef
        a = [{"info": info}]
        a_res = utils.resolve_all(a)
        assert a_res[0]["info"]["Producer"] == self.pdf.doc.info[0]["Producer"]

    def test_decode_psl_list(self):
        a = [PSLiteral("test"), "test_2"]
        assert utils.decode_psl_list(a) == ["test", "test_2"]

    def test_extract_words(self):
        path = os.path.join(HERE, "pdfs/issue-192-example.pdf")
        with pdfplumber.open(path) as pdf:
            p = pdf.pages[0]
            words = p.extract_words(vertical_ttb=False)
            words_attr = p.extract_words(vertical_ttb=False, extra_attrs=["size"])
            words_w_spaces = p.extract_words(vertical_ttb=False, keep_blank_chars=True)
            words_rtl = p.extract_words(horizontal_ltr=False)

        assert words[0]["text"] == "Agaaaaa:"
        assert words[0]["direction"] == 1

        assert "size" not in words[0]
        assert round(words_attr[0]["size"], 2) == 9.96

        assert words_w_spaces[0]["text"] == "Agaaaaa: AAAA"

        vertical = [w for w in words if w["upright"] == 0]
        assert vertical[0]["text"] == "Aaaaaabag8"
        assert vertical[0]["direction"] == -1

        assert words_rtl[1]["text"] == "baaabaaA/AAA"
        assert words_rtl[1]["direction"] == -1

    def test_bad_word_extraction_settings(self):
        with pytest.raises(ValueError):
            self.pdf.pages[0].extract_words(not_real_param=True)

    def test_text_flow(self):
        path = os.path.join(HERE, "pdfs/federal-register-2020-17221.pdf")

        def words_to_text(words):
            grouped = groupby(words, key=itemgetter("top"))
            lines = [" ".join(word["text"] for word in grp) for top, grp in grouped]
            return "\n".join(lines)

        with pdfplumber.open(path) as pdf:
            p0 = pdf.pages[0]
            using_flow = p0.extract_words(use_text_flow=True)
            not_using_flow = p0.extract_words()

        target_text = (
            "The FAA proposes to\n"
            "supersede Airworthiness Directive (AD)\n"
            "2018–23–51, which applies to all The\n"
            "Boeing Company Model 737–8 and 737–\n"
            "9 (737 MAX) airplanes. Since AD 2018–\n"
        )

        assert target_text in words_to_text(using_flow)
        assert target_text not in words_to_text(not_using_flow)

    def test_extract_text(self):
        text = self.pdf.pages[0].extract_text()
        goal_lines = [
            "First Page Previous Page Next Page Last Page",
            "Print",
            "PDFill: PDF Drawing",
            "You can open a PDF or create a blank PDF by PDFill.",
            "Online Help",
            "Here are the PDF drawings created by PDFill",
            "Please save into a new PDF to see the effect!",
            "Goto Page 2: Line Tool",
            "Goto Page 3: Arrow Tool",
            "Goto Page 4: Tool for Rectangle, Square and Rounded Corner",
            "Goto Page 5: Tool for Circle, Ellipse, Arc, Pie",
            "Goto Page 6: Tool for Basic Shapes",
            "Goto Page 7: Tool for Curves",
            "Here are the tools to change line width, style, arrow style and colors",
        ]
        goal = "\n".join(goal_lines)

        assert text == goal
        assert self.pdf.pages[0].crop((0, 0, 1, 1)).extract_text() is None

    def test_intersects_bbox(self):
        objs = [
            # Is same as bbox
            {
                "x0": 0,
                "top": 0,
                "x1": 20,
                "bottom": 20,
            },
            # Inside bbox
            {
                "x0": 10,
                "top": 10,
                "x1": 15,
                "bottom": 15,
            },
            # Overlaps bbox
            {
                "x0": 10,
                "top": 10,
                "x1": 30,
                "bottom": 30,
            },
            # Touching on one side
            {
                "x0": 20,
                "top": 0,
                "x1": 40,
                "bottom": 20,
            },
            # Touching on one corner
            {
                "x0": 20,
                "top": 20,
                "x1": 40,
                "bottom": 40,
            },
            # Fully outside
            {
                "x0": 21,
                "top": 21,
                "x1": 40,
                "bottom": 40,
            },
        ]
        bbox = utils.obj_to_bbox(objs[0])

        assert utils.intersects_bbox(objs, bbox) == objs[:4]

    def test_resize_object(self):
        obj = {
            "x0": 5,
            "x1": 10,
            "top": 20,
            "bottom": 30,
            "width": 5,
            "height": 10,
            "doctop": 120,
            "y0": 40,
            "y1": 50,
        }
        assert utils.resize_object(obj, "x0", 0) == {
            "x0": 0,
            "x1": 10,
            "top": 20,
            "doctop": 120,
            "bottom": 30,
            "width": 10,
            "height": 10,
            "y0": 40,
            "y1": 50,
        }
        assert utils.resize_object(obj, "x1", 50) == {
            "x0": 5,
            "x1": 50,
            "top": 20,
            "doctop": 120,
            "bottom": 30,
            "width": 45,
            "height": 10,
            "y0": 40,
            "y1": 50,
        }
        assert utils.resize_object(obj, "top", 0) == {
            "x0": 5,
            "x1": 10,
            "top": 0,
            "doctop": 100,
            "bottom": 30,
            "height": 30,
            "width": 5,
            "y0": 40,
            "y1": 70,
        }
        assert utils.resize_object(obj, "bottom", 40) == {
            "x0": 5,
            "x1": 10,
            "top": 20,
            "doctop": 120,
            "bottom": 40,
            "height": 20,
            "width": 5,
            "y0": 30,
            "y1": 50,
        }

    def test_move_object(self):
        a = {
            "x0": 5,
            "x1": 10,
            "top": 20,
            "bottom": 30,
            "width": 5,
            "height": 10,
            "doctop": 120,
            "y0": 40,
            "y1": 50,
        }

        b = dict(a)
        b["x0"] = 15
        b["x1"] = 20

        a_new = utils.move_object(a, "h", 10)
        assert a_new == b

    def test_snap_objects(self):
        a = {
            "x0": 5,
            "x1": 10,
            "top": 20,
            "bottom": 30,
            "width": 5,
            "height": 10,
            "doctop": 120,
            "y0": 40,
            "y1": 50,
        }

        b = dict(a)
        b["x0"] = 6
        b["x1"] = 11

        c = dict(a)
        c["x0"] = 7
        c["x1"] = 12

        a_new, b_new, c_new = utils.snap_objects([a, b, c], "x0", 1)
        assert a_new == b_new == c_new

    def test_filter_edges(self):
        with pytest.raises(ValueError):
            utils.filter_edges([], "x")
