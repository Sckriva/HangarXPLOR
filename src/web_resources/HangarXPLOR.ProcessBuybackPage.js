
var HangarXPLOR = HangarXPLOR || {};

/**
 * Processes a loaded buyback page, parsing each pledge and handling pagination
 * @param {jQuery} $page - jQuery object containing the loaded page HTML
 * @param {number} pageNo - The current page number
 */
HangarXPLOR.ProcessBuybackPage = function($page, pageNo) {
  // Find pledges list - selector: section.available-pledges ul.pledges > li
  // An empty page holds a single <li class="no-buy-backs">No pledges available</li>: not a pledge
  var $items = $('section.available-pledges ul.pledges > li', $page).filter(function() { return $('article.pledge, h1', this).length > 0; });

  HangarXPLOR.Log('Processing buyback page', pageNo, 'with', $items.length, 'items');

  // RSI returns the last page again for page numbers past the end: stop on a repeated first pledge too
  var firstId = $('a.holosmallbtn', $items.first()).attr('href') || '';
  var isDuplicate = pageNo > 1 && firstId !== '' && firstId === HangarXPLOR._lastFirstBuybackId;
  HangarXPLOR._lastFirstBuybackId = firstId;

  // Check for empty page
  if ($items.length === 0 || isDuplicate) {
    HangarXPLOR.Log('No items found on buyback page', pageNo, '- finished loading');
    HangarXPLOR.SaveBuybackCache();
    HangarXPLOR.DrawBuybackUI();
    return;
  }

  // Parse each item
  $items.each(function() {
    HangarXPLOR.SafeParseBuybackPledge.apply(this);
  });

  // RSI ignores pagesize on some accounts, so a short page doesn't prove it was the last one:
  // keep going until a page comes back empty or repeated
  if (pageNo < HangarXPLOR._maxBuybackPages) {
    HangarXPLOR.LoadBuybackPage(pageNo + 1);
  } else {
    HangarXPLOR.Log('Buyback loading complete. Total items:', HangarXPLOR._buybackInventory.length);
    HangarXPLOR.SaveBuybackCache();
    HangarXPLOR.DrawBuybackUI();
  }
};
