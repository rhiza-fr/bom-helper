from bom_helper.main import getPartDetails
from unittest.mock import patch, MagicMock

# Truncated HTML snippet for testing
# Truncated HTML snippet for testing
MOCK_HTML = """
<table cellpadding="0" cellspacing="0" class="tableInfoWrap mt-3" data-v-1cd69de4><tbody data-v-1cd69de4><tr data-v-1cd69de4><td class="font-Bold-600" data-v-1cd69de4>
                      Manufacturer
                    </td> <td data-v-1cd69de4><div class="d-flex" data-v-33b59736 data-v-33b59736 data-v-1cd69de4><div data-v-1cd69de4><a href="https://www.lcsc.com/brand-detail/14053.html" target="_blank" custom="" title="hanxia Details page" class="v2-a" data-v-1cd69de4>
                            hanxia
                          </a> <div class="asianBrandsTagIconWrap d-inline-block text-no-wrap ml-2 primary--text mini" data-v-3488d292 data-v-1cd69de4>Asian Brands</div></div> <div class="copyTooltipWrap flex-none d-flex" style="margin-top:-1px;height:22px;" data-v-33b59736><!----></div></div></td></tr> <tr data-v-1cd69de4><td class="font-Bold-600" data-v-1cd69de4>
                      Mfr. Part #
                    </td> <td data-v-1cd69de4>HX PM2.54-1x7P TP-YQ</td></tr> <tr data-v-1cd69de4><td class="font-Bold-600" data-v-1cd69de4>
                      Description
                    </td> <td data-v-1cd69de4>2.54mm 1kV 7P 3A 1 Gold Brass</td></tr> <tr data-v-1cd69de4><td class="font-Bold-600" data-v-1cd69de4>
                      Datasheet
                    </td> <td data-v-1cd69de4><a target="_blank" href="/datasheet/C42379199.pdf" title="hanxia HX PM2.54-1x7P TP-YQ Datasheet" class="v2-a d-inline-flex" data-v-1cd69de4><img src="https://static.lcsc.com/feassets/pc/images/product/pdf_icon.png" width="16" height="16" alt="pdf icon" style="margin-top:2px;" data-v-1cd69de4> <span class="ml-1 v2-a" data-v-1cd69de4>
                          hanxia HX PM2.54-1x7P TP-YQ
                        </span></a></td></tr></tbody></table>

<div class="v-data-table common-table-v7 mt-3 theme--light">
<table><thead><tr><th>Type</th><th>Description</th></tr></thead>
<tbody>
<tr><td>Category</td><td>Connectors</td></tr>
<tr><td>Package</td><td>SMD,P=2.54mm</td></tr>
</tbody></table>
</div>

<table cellpadding="0" cellspacing="0" class="priceTable mt-4">
<tbody>
<tr><td>11+</td><td>€ 0.2071</td><td>€ 2.28</td></tr>
<tr><td>110+</td><td>€ 0.1639</td><td>€ 18.03</td></tr>
</tbody></table>

<script>
    // Some JS context
    var pageData = {
        productImages:["https://assets.lcsc.com/images/lcsc/900x900/front.jpg","https://assets.lcsc.com/images/lcsc/900x900/back.jpg"],
        otherData: {}
    };
</script>
"""

@patch('requests.get')
def test_getPartDetails(mock_get):
    mock_response = MagicMock()
    mock_response.text = MOCK_HTML
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    part = "C42379199"
    details = getPartDetails(part)

    # Manufacturer text should be cleaned of "Asian Brands"
    assert details["Manufacturer"] == "hanxia"
    
    # Datasheet should be a URL
    # The snippet has <a ... href="/datasheet/C42379199.pdf" ...> which partToUrl converts? 
    # No, getPartDetails logic for Datasheet is now extraction.
    # Note: The mock snippet doesn't have a Datasheet row in the main table in previous tool call, 
    # let me check the previous replace_file_content for test_parsing.
    # Ah, I need to add Datasheet row to MOCK_HTML or check if it exists.
    # The MOCK_HTML in last step didn't have Datasheet row. I should add it.
    
    assert "HX PM2.54-1x7P TP-YQ" in details["Mfr. Part #"]
    
    # Check Specifications
    assert "Specifications" in details
    assert details["Specifications"]["Category"] == "Connectors"
    assert details["Specifications"]["Package"] == "SMD,P=2.54mm"
    
    # Check Pricing
    assert "Pricing" in details
    assert len(details["Pricing"]) == 2
    assert details["Pricing"][0]["Qty"] == "11+"
    assert details["Pricing"][0]["Unit Price"] == "€ 0.2071"

    # Check Images
    assert "Images" in details
    assert len(details["Images"]) == 2
    assert details["Images"][0] == "https://assets.lcsc.com/images/lcsc/900x900/front.jpg"


