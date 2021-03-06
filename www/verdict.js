function get_verdict_json()
{
    $.ajax({
      dataType: 'jsonp',
      url: 'http://extras.denverpost.com/app/trial-results/output/config.jsonp',
      success: function () {}
    });
    $.ajax({
      dataType: 'jsonp',
      url: 'http://extras.denverpost.com/app/trial-results/output/numeric.jsonp',
      success: function () {}
    });
    $.ajax({
      dataType: 'jsonp',
      url: 'http://extras.denverpost.com/app/trial-results/output/by_victim.jsonp',
      success: function () {}
    });
}
get_verdict_json();
var refresh_every = 300 * 1000;
var verdict_interval = window.setInterval(function() { get_verdict_json() }, refresh_every);


var verdict = {
    sheet: '',
    numeric: '',
    by_victim: '',
    sheets_loaded: 0,
    item_markup: function(item, charges) 
    {
        return '\n\
<h4 class="victim" id="' + item['slug'] + '">' + item['name_full'] + '</h4>\n\
<ul class="charges">\n\
' + charges + '\
</ul>';
    },
    charge_markup: function(charge, colon)
    {
        return '\
    <li>' + charge['Charge'] + colon + ' <span class="verdict ' + charge['verdict_slug'] + '">' + charge['Verdict'] + '</span></li>\n';
    },
    charge_lookup: function(charge)
    {
        // The official charges are wordy, this makes them less so.
        if ( charge == 'Murder in the first degree, after deliberation and with intent' )
        {
            return 'Murder, first degree, with intent';
        }
        else if ( charge == 'Murder in the first degree, with "universal malice manifesting extreme indifference"' )
        {
            return 'Murder, first degree, with extreme indifference';
        }
        if ( charge == 'Attempted murder in the first degree, after deliberation and with intent' )
        {
            return 'Attempted murder, first degree, with intent';
        }
        else if ( charge == 'Attempted murder in the first degree, with "universal malice manifesting extreme indifference"' )
        {
            return 'Attempted murder, first degree, with extreme indifference';
        }
        return charge;
    },
    verdict_lookup: function(verdict)
    {
        // Verdicts are blank for no verdict, 0 for not guilty by reason of insanity, 1 for guilty and 2 for not guilty
        if ( verdict == '' ) return '';
        else if ( verdict == '0' ) return 'Not guilty by reason of insanity';
        else if ( verdict == '1' ) return 'Guilty';
        else if ( verdict == '2' ) return 'Not guilty';
        return '';
    },
    items: {},
    slugify: function (text)
    {
        // from https://gist.github.com/mathewbyrne/1280286
        return text.toString().toLowerCase()
            .replace(/\s+/g, '-')           // Replace spaces with -
            .replace(/[^\w\-]+/g, '')       // Remove all non-word chars
            .replace(/\-\-+/g, '-')         // Replace multiple - with single -
            .replace(/^-+/, '')             // Trim - from start of text
            .replace(/-+$/, '');            // Trim - from end of text
    },
    tally: function()
    {
        // This is called by the jsonp callbacks. When the counter gets to
        // 2, we have all the data we need and we run init().
        this.sheets_loaded += 1;
        if ( this.sheets_loaded == 2 )
        {
            this.init();
        }
    },
    init: function()
    {
        // Loop through the items, putting each item in this.items indexed by name_full.
        // If we have two items for that last name, we write it to the page.
        $('#charges').html('');
        $.each(this[this['sheet']], function(index, value)
        {
            var key = value['name_full'];
            var write_it = 1;
            var verdict = window.verdict;
            if ( !(key in window.verdict['items']) )
            {
                window.verdict['items'][key] = [];
                write_it = 0;
            }
            window.verdict['items'][key].push(value);

            if ( write_it == 1 )
            {
                // Some items we clean up
                window.verdict['items'][key][0]['Charge'] = verdict.charge_lookup(window.verdict['items'][key][0]['Charge']);
                window.verdict['items'][key][1]['Charge'] = verdict.charge_lookup(window.verdict['items'][key][1]['Charge']);
                window.verdict['items'][key][0]['Verdict'] = verdict.verdict_lookup(window.verdict['items'][key][0]['Verdict']);
                window.verdict['items'][key][1]['Verdict'] = verdict.verdict_lookup(window.verdict['items'][key][1]['Verdict']);

                // Some values we compute.
                window.verdict['items'][key][0]['slug'] = verdict.slugify(window.verdict['items'][key][0]['name_full']);
                window.verdict['items'][key][0]['verdict_slug'] = verdict.slugify(window.verdict['items'][key][0]['Verdict']);
                window.verdict['items'][key][1]['verdict_slug'] = verdict.slugify(window.verdict['items'][key][1]['Verdict']);

                var colon = [':', ':'];
                if ( window.verdict['items'][key][0]['Charge'] == 'Crime of violence (sentence enhancer)' ) colon[0] = '';
                if ( window.verdict['items'][key][1]['Charge'] == 'Crime of violence (sentence enhancer)' ) colon[1] = '';
                var charges_markup = verdict.charge_markup(window.verdict['items'][key][0], colon[0]) + verdict.charge_markup(window.verdict['items'][key][1], colon[1]);
                var markup = verdict.item_markup(window.verdict['items'][key][0], charges_markup);
                $('#charges').append(markup);
            }
        });
        this.items = {};
        this.sheets_loaded = 0;
    }
};

function config_callback(items)
{
    // Load the config. Right now it's just one variable, sheet.
    window.verdict['sheet'] = items[0]['sheet'];
}
function numeric_callback(items)
{
    window.verdict['numeric'] = items;
    window.verdict.tally();
}
function by_victim_callback(items)
{
    window.verdict['by_victim'] = items;
    window.verdict.tally();
}
