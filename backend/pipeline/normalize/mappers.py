"""The mapper for each marketplace. Step 02 normalizes with them; step 01 uses them to judge every row it saves."""
from normalize import depop, ebay, grailed, mercari, poshmark

MAPPERS = {"depop": depop.map_item, "poshmark": poshmark.map_item, "grailed": grailed.map_item,
           "mercari": mercari.map_item, "ebay": ebay.map_item}
