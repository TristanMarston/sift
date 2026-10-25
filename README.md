# Sift

## How Sift collects data with Apify

Calculating cost per wear requires prices, photos, material, condition, shipping, and more. No public dataset offers this kind of data across several marketplaces, so we built our catalog with Apify. We picked one Apify actor per marketplace with fallback actors ready.

Our catalog currently holds **XYZ listings** from 5 marketplaces and 8 categories. In total, it took **XYZ Apify runs** resulting in XYZ raw rows and XYZ clean listings across **XYZ hours**. We collected XYZ photo URLs (XYZ per listing) and about XYZ distinct brands.

### Running at scale

We run actors on five marketplaces in parallel using all five concurrent slots on Apify. To do this, a load balancer plans the run and separates it into batches:

- Data volume is split by ratio and by price. For example, Grailed costs 12 times more per row than Depop, so it gets a much smaller share of the rows.
- The planner reads our Apify balance and sizes the batch so that its worst case fits within the balance.
- Every run goes into a shared Apify dataset so we don't scrape duplicate entries.

Every batch is validated for data integrity. If a marketplace starts returning error codes or empty data, the balancer will switch to a fallback actor and retry. If that actor also fails, it re-allocates rows to other marketplaces. With this system, we can let the load balancer run autonomously overnight.

| Marketplace                  | Items Scraped |
| ---------------------------- | ------------- |
| Depop                        |               |
| Poshmark                     |               |
| Grailed                      |               |
| Mercari                      |               |
| eBay                         |               |

### Processing data

Apify gives us a record of every photo, full description, and structured fields. That means we can call any other tool on it. For listings with no fabric type, we send the photos to Claude Haiku because sellers usually put the care tag near the end. Haiku transcribes the printed text, which costs about $0.0007 per listing.

Across XYZ listings, XYZ state a material and XYZ give percentages. With Haiku scanning labels, we fill in XYZ missing fields.

## Privacy and Transparency

Every extracted fact has a record of its source. It's *verified* if we read it from a care tag, *claimed* if the seller stated it, *inferred* if it's looked up from our product info tables, or *unknown* if the listing does not say. We never fill in blanks with guesses. We keep exact text so receipts can quote the original. Final prices include buyer fees and shipping.

We do not store seller usernames, profile links, or account IDs. A scanner checks all data after every batch and stops collection if any identity information is found. We scrape only public listing data with no accounts needed. Original photos are shown and links go to the marketplace. User-uploaded photos are used only for search matching.