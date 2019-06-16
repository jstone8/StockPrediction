// Reference: https://www.w3schools.com/howto/howto_js_filter_table.asp
function filterTable() {
    var input = document.getElementById("seach-portfolio"),
        filter = input.value.toUpperCase(),
        table = document.getElementById("scroll-portfolio"),
        tr = table.getElementsByTagName("tr");

    for (var i = 0; i < tr.length; i++) {
        var td = tr[i].getElementsByTagName("td")[1];

        if (td) {
            var txtValue = td.textContent || td.innerText;
            
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                tr[i].style.display = "";
            } 
            else {
                tr[i].style.display = "none";
            }
        }       
    }
}

function showTable(tableId) {
    if (tableId == "holding-detail") {
        document.getElementById("table-title").innerHTML = "<div>Portfolio Details</div>";
        document.getElementById("transaction-history").style.display = "none";
    }
    else {
        document.getElementById("table-title").innerHTML = "<div>Transaction History</div>";
        document.getElementById("holding-detail").style.display = "none";
    }

    document.getElementById(tableId).style.display = "block";
}