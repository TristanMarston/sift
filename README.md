<p align="center"><img src="demo/branding/sift-logo.png" alt="Sift logo" width="200"></p>

## Inspiration

We believe that everyone wants what's best for them and what's best for the environment. But in the current shopping landscape, both are ambiguous. Everything is sorted by price, so nobody can tell whether a purchase pays off over years of wear, or whether it just means buying more junk, and feeding the landfill, more often.

As busy people with busy lives, we wish we could do more to care for ourselves and for the planet. Sift addresses both. It reduces the friction for people who want to be mindful, good consumers, and in the end, it improves their lives.

## What it does

Take a photo of anyone or any garment. Sift searches through online marketplaces like Depop, Poshmark, and eBay for look-alikes and ranks them for you and for the planet.

- *For you*: we calculate cost per wear, because a $20 shirt that you throw out after 30 uses ends up being more expensive than a $40 shirt that lasts 80 uses.
- *For the planet*: we calculate an eco score built from verifiable facts like fabric, durability, shipping distance, and second life potential.

## How we gathered the data

Calculating cost per wear requires prices, photos, material, condition, shipping, and more. No public dataset offers this kind of data across several marketplaces, so we built our catalog with Apify. We picked one Apify actor per marketplace with fallback actors ready.

Our catalog currently holds almost **150,000 listings** from 5 marketplaces and 8 clothing categories. In total, it took nearly **2000 Apify runs** across over **12 hours**. We collected over **800,000 photo URLs** and around **7000 distinct brands**.

### Running at scale

We run actors on five marketplaces in parallel using all five concurrent slots on Apify. To do this, a load balancer plans the run and separates it into batches:

- Data volume is split by ratio and by price. For example, Grailed costs 12 times more per row than Depop, so it gets a much smaller share of the rows.
- The planner reads our Apify balance and sizes the batch so that its worst case fits within the balance.
- Every run goes into a shared Apify dataset to prevent duplicates.

Every batch is validated for data integrity. If a marketplace starts returning error codes or empty data, the balancer will switch to a fallback actor and retry. If that actor also fails, it re-allocates rows to other marketplaces. With this system, we can let the load balancer run autonomously overnight.

### Processing data

Apify gives us a record of every photo, full description, and structured fields. That means we can call any other tool on it. For listings with no fabric type, we send the photos to Claude Haiku because sellers usually put the care tag near the end. Haiku transcribes the printed text, which costs about $0.0007 per listing.

### Privacy and Transparency

- We collect only public listing data with no accounts needed (the same information any visitor sees in a browser).
- All links go directly to the marketplace.
- User-uploaded photos are used only for search matching.
- We do not store seller usernames or profile information. A scanner checks all data after every batch and stops collection if any identity information is found.

## Image detection and matching

A segmentation model (SegFormer) draws a box around each garment in the photo. Claude Haiku then looks at each cropped box and names it ("black leather jacket") and reads the brand if a logo or label is visible. If Haiku fails, SegFormer's own labels are the fallback.

A fashion-trained image model (FashionSigLIP) embeds each garment into a 768-dimensional vector so similar clothes are close together. With this unified data format, we can easily identify pieces of clothing that are similar to the ones that the user sends. After additional testing, we added an additional vector score correction on top of the vector search, which will be explained later.

## Cost per wear and eco score

Expected wears (for calculating cost per wear) are derived from an EU public baseline, adjusted by multipliers for quality and condition. We then divide the item's full price, including shipping and buyer fees, by those expected wears.

Every item is already secondhand, so we score how good it is for the planet by determining what it's made of, how long it should last, how far it travels to reach you, and whether it has second life potential. Each result also shows how it ranks against the other matches in your search (ex. "Greener than 83% of listings")

## Challenges we ran into

- Our catalog had to come from five different marketplaces. We also needed the full description, every photo, condition, size, and shipping information. Writing and maintaining scrapers that deal with proxies and layout changes would have taken most of our time. Apify actors handled that for us. We chose one actor per marketplace, and each one returns the full listing as structured data. That left our time for the interesting part of exploring the data and ranking items by cost per wear.
- Most listings don't include fabric data, and fabric is the biggest indicator to how long a garment lasts. Sellers usually include a photo of the care tag, so we send those photos to Claude Haiku to transcribe the printed text and fill in missing fields.
- No single database covers eco facts for secondhand clothes either, so we built one from sources we checked ourselves. It includes brand repair programs, B Corp and bluesign certifications, and the EU's published wear baselines.

## What we learned

- The state of sustainability data is very scattered. There's no single place to look up how long a garment lasts or how eco-friendly a brand is, so a lot of the work was compiling sources ourselves.
- Data monitoring is extremely important. Our load balancer began as a simple script to check for empty data, but building it into an automated system saved us from constantly monitoring every batch of data.

## What's next

We're looking to expand to personalized "fit" predictions and local pickup consideration to cut shipping emissions. We're also exploring verified reviews where users submit photos after one year of buying an item so we gather durability data. Our goal is to build Sift into a broader service that makes mindful shopping easy for everyone.
