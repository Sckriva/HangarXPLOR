
var HangarXPLOR = HangarXPLOR || {};

/**
 * Loads a page of buyback pledges via AJAX
 * @param {number} pageNo - The page number to load (1-indexed)
 */
HangarXPLOR._maxBuybackPages = 100;

HangarXPLOR.LoadBuybackPage = function(pageNo, retryCount) {
  pageNo = pageNo || 1;
  retryCount = retryCount || 0;

  HangarXPLOR.Log('Loading buyback page', pageNo);
  HangarXPLOR.UpdateStatus(pageNo);

  $.ajax({
    url: '/account/buy-back-pledges?page=' + pageNo + '&pagesize=50',
    method: 'GET',
    dataType: 'html',
    success: function(response) {
      HangarXPLOR.ProcessBuybackPage($(response), pageNo);
    },
    error: function(xhr, status, error) {
      // Same rate-limit handling as the hangar loader (HangarXPLOR.LoadPage)
      if (xhr.status === 429 && retryCount < HangarXPLOR._maxRetries) {
        var delay = HangarXPLOR._retryDelay * (retryCount + 1);
        HangarXPLOR.UpdateStatus(pageNo, 'rate-limited', retryCount + 1, delay / 1000);
        setTimeout(function() { HangarXPLOR.LoadBuybackPage(pageNo, retryCount + 1); }, delay);
        return;
      }
      HangarXPLOR.Log('Error loading buyback page', pageNo, status, error);
      // Still try to render what we have
      HangarXPLOR.SaveBuybackCache();
      HangarXPLOR.DrawBuybackUI();
    }
  });
};
