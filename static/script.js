var chartWidth = 873, chartHeight = 350,
    datafile = 'data/portfolio';

var margin = {top: 75, right: 10, bottom: 90, left: 35},
    margin2 = {top: 290, right: 10, bottom: 20, left: 35},
    width = chartWidth - margin.left - margin.right,
    height = chartHeight - margin.top - margin.bottom,
    height2 = chartHeight - margin2.top - margin2.bottom;

var parseDate = d3.time.format('%Y-%m-%d').parse,
    bisectDate = d3.bisector(function(d) { return d.date; }).left,
    timeFormat = d3.time.format('%b %d, %Y');

var x = d3.time.scale().range([0, width]),      // For the focus part
    x2 = d3.time.scale().range([0, width]),     // For the context part
    y = d3.scale.linear().range([height, 0]),
    y2 = d3.scale.linear().range([height2, 0]);

var xAxis = d3.svg.axis().scale(x).orient('bottom'),
    xAxis2 = d3.svg.axis().scale(x2).orient('bottom'),
    yAxis = d3.svg.axis().scale(y).orient('left');

var benchmarkLine = d3.svg.line()
    .x(function(d) { return x(d.date); })
    .y(function(d) { return y(d.benchmark); });

var portfolioLine = d3.svg.line()
    .x(function(d) { return x(d.date); })
    .y(function(d) { return y(d.portfolio); });

var contextArea = d3.svg.area()
    .x(function(d) { return x2(d.date); })
    .y0(height2)
    .y1(function(d) { return y2(d.benchmark); });

var svg = d3.select('#svg').append('svg')
    .attr('class', 'chart')
    //.attr('width', chartWidth)            // Fix-size graphic
    //.attr('height', chartHeight);
    .attr('width', '100%')                  // Responsive graphic
    .attr('height', '100%')
    .attr('viewBox','0 0 ' + chartWidth + ' ' + chartHeight)
    .attr('preserveAspectRatio','xMinYMin meet');

svg.append('g')
    .attr('class', 'chart-title')
    .append('text')
    .style('text-anchor', 'middle')
    .attr('x', chartWidth / 2)
    .attr('y', 25)
    .text('Portfolio Performance');

svg.append('defs').append('clipPath')
    .attr('id', 'clip')
    .append('rect')
    .attr('width', width)
    .attr('height', height);

var focus = svg.append('g')
    .attr('class', 'focus')
    .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

var context = svg.append('g')
    .attr('class', 'context')
    .attr('transform', 'translate(' + margin2.left + ',' + margin2.top + ')');

d3.csv(datafile, type, function(error, data) {
    if (error) throw error;

    var brush = d3.svg.brush().x(x2).on('brush', brushed);

    var xRange = d3.extent(data.map(function(d) { return d.date; })),
        benchmarkRange = d3.extent(data.map(function(d) { return d.benchmark; })),
        portfolioRange = d3.extent(data.map(function(d) { return d.portfolio; })),
        yRange = [Math.min(benchmarkRange[0], portfolioRange[0]) / 1.03, 
                  Math.max(benchmarkRange[1], portfolioRange[1]) * 1.03];

    var dateRange = ['1w', '1m', '3m', '6m', '1y', 'All'],
        optionWidth = 28, optionHeight = 20;

    /* Zoom and legend */
    var timeInfo = svg.append('g')
        .attr('class', 'time-info')
        .attr('transform', 'translate(' + margin2.left + ', 55)');

    timeInfo.append('g').append('text').text('Zoom');

    // Add options for the date range
    var rangeOption = timeInfo.selectAll('.range-option')
        .data(dateRange)
        .enter().append('g')
        .attr('class', 'range-option');

    rangeOption.append('rect')
        .attr('width', optionWidth)
        .attr('height', optionHeight)
        .attr('transform', function(d, i) { 
            return 'translate(' + ((optionWidth + 5) * i + 40) + ', -13)'; 
        });

    rangeOption.append('text')
        .attr('x', function(d, i) { return (optionWidth + 5) * i + optionWidth / 2 + 40; })
        .attr('y', 0)
        .style('text-anchor', 'middle')
        .text(function(d) { return d; })
        .on('click', function(d) { selectTimeRange(d); });

    // Add legend to show the date range for the current window
    var timeRange = timeInfo.append('text')
        .text(timeFormat(new Date(xRange[0])) + ' - ' + timeFormat(new Date(xRange[1])))
        .style('text-anchor', 'end')
        .attr('transform', 'translate(' + (width - 10) + ', 0)');

    /* Focus */
    x.domain(xRange);
    y.domain(yRange);
    x2.domain(x.domain());
    y2.domain(y.domain());

    // Benchmark line
    var benchmark = focus.append('path')
        .datum(data)
        .attr('class', 'line benchmark-line')
        .attr('d', benchmarkLine);

    // Portfolio line
    var portfolio = focus.append('path')
        .datum(data)
        .attr('class', 'line portfolio-line')
        .attr('d', portfolioLine);

    var focusAxis = focus.append('g')
        .attr('class', 'axis axis-x')
        .attr('transform', 'translate(0 ,' + height + ')')
        .call(xAxis);

    formatAxisX(focusAxis);

    // Format y axis
    focus.append('g')
         .attr('class', 'axis axis-y')
         .attr('transform', 'translate(0, 0)')
         .call(yAxis.ticks(6).tickFormat(function(d) { 
            return parseInt(d / 1000) + 'k'; 
         }));

    // Add y grid lines
    focus.append('g')
        .attr('class', 'y-grid')
        .call(d3.svg.axis().scale(y).orient('left')
                    .ticks(5).tickSize(-width, 0, 0).tickFormat(''));

    /* Tooltip */
    var hoverLine = focus.append('g')
        .attr('class', 'hover-line')
        .append('line')
        .style('display', 'none')
        .attr('y1', 0)
        .attr('y2', height);

    var hoverText = d3.select('#svg').append('div')
        .attr('class', 'hover-text')
        .style('display', 'none');

    var benchmarkTooltip = focus.append('g')
        .attr('class', 'tooltip benchmark-tooltip')
        .append('circle')
        .style('display', 'none')
        .attr('r', 3.5);

    var portfolioTooltip = focus.append('g')
        .attr('class', 'tooltip portfolio-tooltip')
        .append('circle')
        .style('display', 'none')
        .attr('r', 3.5);

    // Overlay window for tooltips
    svg.append('rect')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
        .attr('class', 'overlay')
        .attr('width', width)
        .attr('height', height)
        .on('mouseover', function() {
            hoverLine.style('display', null);
            hoverText.style('display', null);
            benchmarkTooltip.style('display', null);
            portfolioTooltip.style('display', null);
        })
        .on('mouseout', function() {
            hoverLine.style('display', 'none');
            hoverText.style('display', 'none');
            benchmarkTooltip.style('display', 'none');
            portfolioTooltip.style('display', 'none');
        })
        .on('mousemove', mousemove);

    /* Context  */
    context.append('path')
            .datum(data)
            .attr('class', 'area')
            .attr('d', contextArea);

    var contextAxis = context.append('g')
            .attr('class', 'axis axis-x')
            .attr('y', 0)
            .attr('transform', 'translate(0,' + height2 + ')')
            .call(xAxis2);

    formatAxisX(contextAxis);

    context.append('g')
            .attr('class', 'brushX')
            .call(brush)
            .selectAll('rect')
            .attr('height', height2);

    context.select('g.brushX').call(brush.extent([xRange[0], xRange[1]]));

    /* Functions */
    function brushed() {
        x.domain(brush.empty() ? x2.domain() : brush.extent());
        
        if (!brush.empty()) {
            var ext = brush.extent();
            y.domain([
                d3.min(data.map(function(d) { 
                    return (d.date >= ext[0] && d.date <= ext[1]) ? d.benchmark : yRange[1]; })) / 1.03,
                d3.max(data.map(function(d) { 
                    return (d.date >= ext[0] && d.date <= ext[1]) ? d.benchmark : yRange[0]; })) * 1.03
            ]);
            timeRange.text(timeFormat(new Date(ext[0])) + ' - ' + timeFormat(new Date(ext[1])));
        }
        else {
            y.domain(yRange);
            timeRange.text(timeFormat(new Date(xRange[0])) + ' - ' + timeFormat(new Date(xRange[1])));
        }

        portfolio.attr('d', portfolioLine);
        benchmark.attr('d', benchmarkLine);
        
        formatAxisX(focus.select('.axis.axis-x').call(xAxis));
        focus.select('.axis.axis-y')
             .call(yAxis.ticks(6).tickFormat(function(d) { 
                 return parseInt(d / 1000) + 'k';
             }));
    }

    function mousemove() {
        var x0 = x.invert(d3.mouse(this)[0]),
            i = bisectDate(data, x0, 1),
            d0 = data[i - 1],
            d1 = data[i],
            d = x0 - d0.date > d1.date - x0 ? d1 : d0;
        
        hoverLine.attr('x1', x(d.date)).attr('x2', x(d.date));
        hoverText.style('top', d3.event.pageY + 'px')
                 .style('left', function() {
                     if (x(d.date) < width / 2) return (d3.event.pageX + 12) + 'px';
                     return (d3.event.pageX - 12) + 'px';
                 })
                 .style('transform', function() {
                     if (x(d.date) < width / 2) return 'translate(0, -50%)';
                     return 'translate(-100%, -50%)';
                 })
                 .html(function() {
                     var msg = timeFormat(d.date) + ': <br/>';
                     msg += "<span class='dot portfolio-dot'></span>";
                     msg += 'Portfolio: $' + d3.format(',.2f')(d.portfolio) + '<br/>';
                     msg += "<span class='dot benchmark-dot'></span>";
                     msg += 'Benchmark: $' + d3.format(',.2f')(d.benchmark);
                     return msg;
                 });

        benchmarkTooltip.attr('transform', 'translate(' + x(d.date) + ',' + y(d.benchmark) + ')');
        portfolioTooltip.attr('transform', 'translate(' + x(d.date) + ',' + y(d.portfolio) + ')');
    }

    function selectTimeRange(range) {
        var start = new Date(xRange[1]), end = new Date(xRange[1]);

        if      (range === '1m') start.setMonth(start.getMonth() - 1);
        else if (range === '1w') start.setDate(start.getDate() - 7);
        else if (range === '3m') start.setMonth(start.getMonth() - 3);
        else if (range === '6m') start.setMonth(start.getMonth() - 6);
        else if (range === '1y') start.setFullYear(start.getFullYear() - 1);
        else                     start = new Date(xRange[0]);

        start = d3.max([start, xRange[0]]);

        brush.extent([start, end]);
        brushed();
        context.select('g.brushX').call(brush.extent([start, end]));
    }
})

function type(d) {
    return {
        date      : parseDate(d.date),
        benchmark : +d.benchmark,
        portfolio : +d.total_value,
    };
}

function formatAxisX(axis) {
    axis.selectAll('.tick').each(function(d) {
        if (this.textContent === d3.time.format('%B')(d)) {
          d3.select(this).select('text').text(d3.time.format('%b')(d))
        };
    });
}