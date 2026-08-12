# Broken Link Crawler

This is a python program with a basic UI that is engineered to go through websites and find pages that do not work and/or out of order. It then generates a simple report for you to find exactly what is wrong so you know exactly what to fix. But main problem is it takes a few minutes to go through the pages and generate the report.

## How it works

So this program works due to 9 files:
First, index.html is what gives this program a UI that users can interact with and input the website URL.
Second, main.py is what takes care of most of the python and the logic part of this program, allowing it to get the link, crawl it, and then effectively generate a report for the user.
Then there is crawler.py, and this is what walks the site, page by page, to get everything that isn't working.
fetch_page.py on the other hand, downloads pages and then gets the URLs within them to then checkout.
check_link.py checks if the links are working or dead.
Going on, report.py is what takes all of the raw data and turns it into a actual report that users can understand.
And then we have queries.py and db.py, and both of these files store everything in Postgres.
Finally, worker.py runs the crawl in chunks so that Vercel doesnt cut it off.

## AI Usage

When it comes to AI, I only used it for minimal tasks, like debugging difficult errors, committing to github, and hosting when I had trouble with Vercel. So I can confidently say that I used AI below the 30% mark.
