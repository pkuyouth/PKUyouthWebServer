"use strict";

import newsTr from '.news_component.js'
import '../vendor/axios.min.js'

const ApiUrl = widows.url;

var vm = new Vue({
    el: "#table",


    components: {
        "news-tr": newsTr,
    }

    data: {
        newsInfo,
    },

    created() {

    },

})

