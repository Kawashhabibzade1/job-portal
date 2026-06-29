import time
import unittest

from app.models import JobPosting
from app.providers.scraped import _parse_indeed, _parse_linkedin
from app.services.cache import MemoryCache
from app.services.deduplicate import deduplicate_jobs


class CacheTests(unittest.TestCase):
    def test_cache_expires(self):
        cache = MemoryCache()
        cache.set("python_berlin_indeed", ["job"], ttl_ms=10)
        self.assertEqual(cache.get("python_berlin_indeed"), ["job"])
        time.sleep(0.02)
        self.assertIsNone(cache.get("python_berlin_indeed"))


class DeduplicationTests(unittest.TestCase):
    def test_merges_similar_title_same_company_with_source_priority(self):
        jobs = [
            JobPosting(
                title="Senior Python Developer",
                company="Acme",
                location="Berlin",
                source="LinkedIn",
                apply_url="https://linkedin.com/jobs/view/1",
            ),
            JobPosting(
                title="Senior Python Developer",
                company="Acme",
                location="Berlin",
                source="Indeed",
                apply_url="https://de.indeed.com/viewjob?jk=1",
            ),
        ]

        unique = deduplicate_jobs(jobs)

        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0].source, "Indeed")
        self.assertEqual(unique[0].sources, ["Indeed", "LinkedIn"])


class ParserTests(unittest.TestCase):
    def test_parse_indeed_card(self):
        html = """
        <div data-testid="job-card">
          <h2><a href="/viewjob?jk=abc">Python Developer</a></h2>
          <span data-testid="company-name">Acme GmbH</span>
          <div data-testid="job-location">Berlin</div>
          <div data-testid="salary">60.000 EUR</div>
        </div></div>
        """

        jobs = _parse_indeed(html)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Python Developer")
        self.assertEqual(jobs[0].company, "Acme GmbH")
        self.assertEqual(jobs[0].salary_text, "60.000 EUR")

    def test_parse_linkedin_card(self):
        html = """
        <li data-job-id="123">
          <h3 class="base-search-card__title">Data Scientist</h3>
          <h4 class="base-search-card__company-name">Acme</h4>
          <span class="job-search-card__location">Hamburg</span>
        </li>
        """

        jobs = _parse_linkedin(html)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Data Scientist")
        self.assertEqual(jobs[0].apply_url, "https://www.linkedin.com/jobs/view/123")


if __name__ == "__main__":
    unittest.main()
