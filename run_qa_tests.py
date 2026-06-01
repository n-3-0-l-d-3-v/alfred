"""
Phase 5 QA Test Runner (No pytest required)
Runs all QA tests and generates a detailed report
"""

import sys
import traceback
from io import StringIO

# Import test classes
from test_phase5_qa import (
    TestEmotionAccuracy,
    TestMemeRelevance,
    TestToneBalance,
    TestEdgeCases,
    TestUXQuality,
    TestIntegration
)

class QATestRunner:
    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "errors": []
        }
        self.test_classes = [
            TestEmotionAccuracy,
            TestMemeRelevance,
            TestToneBalance,
            TestEdgeCases,
            TestUXQuality,
            TestIntegration
        ]

    def run_test(self, test_class, test_method_name):
        """Run a single test method"""
        test_name = f"{test_class.__name__}.{test_method_name}"
        try:
            test_instance = test_class()
            test_method = getattr(test_instance, test_method_name)
            test_method()
            return True, None
        except AssertionError as e:
            return False, str(e)
        except Exception as e:
            return False, f"{type(e).__name__}: {str(e)}"

    def run_all(self):
        """Run all tests"""
        for test_class in self.test_classes:
            # Get all test methods
            test_methods = [m for m in dir(test_class) if m.startswith("test_")]
            
            for test_method in test_methods:
                passed, error = self.run_test(test_class, test_method)
                test_name = f"{test_class.__name__}.{test_method}"
                
                if passed:
                    self.results["passed"].append(test_name)
                else:
                    self.results["failed"].append((test_name, error))

    def generate_report(self):
        """Generate detailed QA report"""
        total_tests = len(self.results["passed"]) + len(self.results["failed"])
        passed_count = len(self.results["passed"])
        failed_count = len(self.results["failed"])
        pass_rate = (passed_count / total_tests * 100) if total_tests > 0 else 0

        report = []
        report.append("\n" + "="*80)
        report.append("PHASE 5 QA TEST REPORT - EMOTION ENGINE + MEME COMPILER")
        report.append("="*80)

        # Summary
        report.append(f"\nTEST SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Tests:     {total_tests}")
        report.append(f"Passed:          {passed_count} ✅")
        report.append(f"Failed:          {failed_count} ❌")
        report.append(f"Pass Rate:       {pass_rate:.1f}%")

        # Passed tests by category
        if self.results["passed"]:
            report.append(f"\n✅ PASSED TESTS ({passed_count})")
            report.append("-" * 80)
            
            # Group by category
            categories = {}
            for test_name in self.results["passed"]:
                category = test_name.split(".")[0]
                if category not in categories:
                    categories[category] = []
                categories[category].append(test_name)
            
            for category in sorted(categories.keys()):
                report.append(f"\n  {category}:")
                for test_name in categories[category]:
                    test_method = test_name.split(".")[-1]
                    report.append(f"    ✅ {test_method}")

        # Failed tests
        if self.results["failed"]:
            report.append(f"\n❌ FAILED TESTS ({failed_count})")
            report.append("-" * 80)
            
            for test_name, error in self.results["failed"]:
                report.append(f"\n  {test_name}")
                report.append(f"    Error: {error}")

        # Test Categories Coverage
        report.append(f"\n\nTEST CATEGORY COVERAGE")
        report.append("-" * 80)
        
        categories = {
            "TestEmotionAccuracy": ("Emotion Accuracy", 
                "Does emotion match code quality?"),
            "TestMemeRelevance": ("Meme Relevance",
                "Are memes related to detected patterns?"),
            "TestToneBalance": ("Tone Balance",
                "Not too harsh, not too boring?"),
            "TestEdgeCases": ("Edge Cases",
                "No crashes, handles gracefully?"),
            "TestUXQuality": ("UX Quality",
                "Is it engaging?"),
            "TestIntegration": ("Integration",
                "Full workflow paths")
        }

        for test_class_name, (category_name, description) in categories.items():
            passed_in_cat = len([t for t in self.results["passed"] if test_class_name in t])
            failed_in_cat = len([t for t in self.results["failed"] if test_class_name in t[0]])
            total_in_cat = passed_in_cat + failed_in_cat
            
            status = "✅ PASS" if failed_in_cat == 0 and total_in_cat > 0 else "⚠️  FAIL" if failed_in_cat > 0 else "⏭️  SKIP"
            
            report.append(f"\n{status} - {category_name}")
            report.append(f"    {description}")
            if total_in_cat > 0:
                report.append(f"    Tests: {passed_in_cat}/{total_in_cat} passed")

        # Verdict
        report.append(f"\n\nFINAL VERDICT")
        report.append("="*80)
        
        if failed_count == 0 and passed_count > 0:
            verdict = "✅ READY FOR PRODUCTION"
            report.append(f"\n{verdict}")
            report.append("\nAll QA tests passed. Phase 5 implementation is solid.")
            report.append("- Emotion detection is accurate")
            report.append("- Memes are relevant and not overused")
            report.append("- Tone is balanced and engaging")
            report.append("- Edge cases are handled gracefully")
            report.append("- UX quality is good")
        elif pass_rate >= 80:
            verdict = "⚠️  READY WITH MINOR ISSUES"
            report.append(f"\n{verdict}")
            report.append(f"\n{pass_rate:.0f}% of tests passed. See failed tests above for details.")
        else:
            verdict = "❌ NOT READY"
            report.append(f"\n{verdict}")
            report.append(f"\nOnly {pass_rate:.0f}% of tests passed. Fix failed tests before deployment.")

        report.append("\n" + "="*80)

        return "\n".join(report)

    def run_and_report(self):
        """Run all tests and generate report"""
        print("Running Phase 5 QA Tests...")
        self.run_all()
        report = self.generate_report()
        print(report)
        return report


if __name__ == "__main__":
    runner = QATestRunner()
    runner.run_and_report()
