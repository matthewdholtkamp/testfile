import unittest
from scripts.pipeline_utils import normalize_section_header

class TestSectionMapping(unittest.TestCase):

    def test_methods(self):
        self.assertEqual(normalize_section_header("Materials and Methods"), "Methods")
        self.assertEqual(normalize_section_header("materials and methods"), "Methods")
        self.assertEqual(normalize_section_header("Material and Methods"), "Methods")
        self.assertEqual(normalize_section_header("Methodology"), "Methods")
        self.assertEqual(normalize_section_header("Methods"), "Methods")
        self.assertEqual(normalize_section_header("  methods  "), "Methods")
        self.assertEqual(normalize_section_header("Materials & Methods"), "Methods")

    def test_results_and_discussion(self):
        # Spec: treat as Results
        self.assertEqual(normalize_section_header("Results and Discussion"), "Results")
        self.assertEqual(normalize_section_header("results and discussion"), "Results")
        self.assertEqual(normalize_section_header("Results & Discussion"), "Results") # "Results & Discussion" -> "Results".

    def test_discussion(self):
        self.assertEqual(normalize_section_header("Discussion"), "Discussion")
        self.assertEqual(normalize_section_header("General Discussion"), "Discussion")
        # Conclusion -> Discussion
        self.assertEqual(normalize_section_header("Conclusion"), "Discussion")
        self.assertEqual(normalize_section_header("Conclusions"), "Discussion")
        self.assertEqual(normalize_section_header("Conclusion and Future Work"), "Discussion")

    def test_introduction(self):
        self.assertEqual(normalize_section_header("Introduction"), "Introduction")
        self.assertEqual(normalize_section_header("Background"), "Introduction")
        self.assertEqual(normalize_section_header("Theoretical Background"), "Introduction")

    def test_tables(self):
        self.assertEqual(normalize_section_header("Table 1"), "Tables")
        self.assertEqual(normalize_section_header("Tables"), "Tables")
        self.assertEqual(normalize_section_header("Supplementary Table"), "Tables")
        self.assertEqual(normalize_section_header("Tab. 1"), "Tables")
        self.assertEqual(normalize_section_header("Tbl 2"), "Tables")

    def test_figures(self):
        self.assertEqual(normalize_section_header("Figure 2"), "Figures")
        self.assertEqual(normalize_section_header("Figures"), "Figures")
        self.assertEqual(normalize_section_header("Fig 1"), "Figures")
        self.assertEqual(normalize_section_header("Fig. 1"), "Figures")
        self.assertEqual(normalize_section_header("Figs"), "Figures")
        self.assertEqual(normalize_section_header("List of Figures"), "Figures")

    def test_other(self):
        self.assertEqual(normalize_section_header("Supplement"), "Other")
        self.assertEqual(normalize_section_header("Supplementary Material"), "Other")
        self.assertEqual(normalize_section_header("Appendix"), "Other")
        self.assertEqual(normalize_section_header("Acknowledgements"), "Other")
        self.assertEqual(normalize_section_header("References"), "Other")
        self.assertEqual(normalize_section_header(""), "Other")
        self.assertEqual(normalize_section_header(None), "Other")

    def test_results_fallback(self):
        # Fallback for plain Results
        self.assertEqual(normalize_section_header("Results"), "Results")
        self.assertEqual(normalize_section_header("Experimental Results"), "Results")

if __name__ == '__main__':
    unittest.main()
