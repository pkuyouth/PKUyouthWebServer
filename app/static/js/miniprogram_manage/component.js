"use strict";

Vue.component('news-tr',{
    props: ['news'],
    data() {
        return {

        }
    },
    computed: {
        newsID() { return this.news.newsID },
        column() { return this.news.column.substring(0,10) },
        masssend_time() { return this.news.masssend_time.substring(0,10) },
        read_num() { return this.news.read_num },
        like_num() { return this.news.like_num },
        content_url() { return this.news.content_url },
        in_use() { return this.news.in_use },
    },
    template: '\
        <tr>\
            <td class="font-weight-bold">{{ newsID }}</td>\
            <td>{{ masssend_time }}</td>\
            <td>{{ column }}</td>\
            <td><a href="{{ content_url }}" target="_blank" class="text-primary">{{ title }}</a></td>\
            <td>{{ read_num }}</td>\
            <td>{{ like_num }}</td>\
            <td in-use="{{ in_use }}">\
                <button v-if="in_use" type="button" class="btn btn-outline-success" onclick="tapUseBtn";>Use</button>\
                <button v-else type="button" class="btn btn-outline-primary" onclick="tapUseBtn";>Discard</button>\
            </td>\
        </tr>\
    ',
    methods: {
        tapUseBtn() {
            console.log(this.newsID);
        }
    }
})
