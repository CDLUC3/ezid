/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

// ##### Gulp Tasks #####

var { src, dest, watch, series, parallel } = require('gulp');
var sass = require('gulp-sass')(require('node-sass'));
var autoprefixer = require('gulp-autoprefixer');
var browserSync = require('browser-sync');
var server = browserSync.create();
var useref = require('gulp-useref');
var uglify = require('gulp-uglify');
var gulpIf = require('gulp-if');
var cleanCSS = require('gulp-clean-css');
var imagemin = require('gulp-imagemin');
var cache = require('gulp-cache');
var del = require('del');
var modernizr = require('gulp-modernizr');
var stylelint = require('stylelint');
var jshint = require('gulp-jshint');
var lbInclude = require('gulp-lb-include');
var ssi = require('browsersync-ssi');
var postcss = require('gulp-postcss');
var assets = require('postcss-assets');
var ghPages = require('gulp-gh-pages');

// Public Tasks:

exports.default = parallel(scss, start, watcher);

// exports.build = series(clean, fonts, scsslint_legacy, scsslint, jslint, scss_legacy, scss, assemble, minifyCss, copyimages, fonts);
exports.build = series(clean, fonts, jslint, scss_legacy, scss, assemble, minifyCss, copyimages, fonts, copyCSS);

exports.upload = githubpages;

exports.modernizr = runmodernizr;

// Process scss to css, add sourcemaps, inline font & image files into css:

sass.compiler = require('node-sass');

function scss(cb) {
  return src('dev/scss/*.scss', { sourcemaps: true })
  .pipe(sass().on('error', sass.logError))
  .pipe(autoprefixer('last 2 versions'))
  .pipe(postcss([assets({
    loadPaths: ['fonts/', 'images/']
  })]))
  .pipe(dest('dev/css', { sourcemaps: 'sourcemaps' }))
  .pipe(browserSync.stream());
  cb();
}

function scss_legacy(cb) {
  return src('dev/legacy-scss/*.scss', { sourcemaps: true })
  .pipe(sass().on('error', sass.logError))
  .pipe(autoprefixer('last 2 versions'))
  .pipe(dest('dev/legacy-scss/css', { sourcemaps: 'sourcemaps' }))
  .pipe(browserSync.stream());
  cb();
}

// Watch scss, html, and js and reload browser if any changes:

function watcher(cb) {
  watch('dev/scss/*.scss', series(scss, refresh, scsslint));
  watch('dev/js/*.js', series(jslint, refresh));
  watch('dev/**/*.html', refresh);
  cb();
}

function refresh(cb) {
  server.reload()
  cb();
}

function start(cb) {
  server.init({
    open: false,
    reloadOnRestart: true,
    server: {
      baseDir: 'dev',
      middleware: ssi({
        baseDir: __dirname + '/dev',
        ext: '.html',
        version: '1.4.0'
      })
    }
  })
  cb();
}

// Minify and uglify css and js from paths within useref comment tags in html:

function assemble(cb) {
  return src(['dev/**/*.html', '!dev/includes/*', 'dev/css/*.css'])
  .pipe(gulpIf('*.js', uglify()))
  .pipe(useref())
  .pipe(lbInclude()) // parse <!--#include file="" --> statements
  .pipe(dest('ui_library'))
  cb();
}

function minifyCss(cb) {
  return src(['dev/css/*.css'])
  .pipe(cleanCSS({debug: true, level: 2}, (details) => {
    console.log(`${details.name}: ${details.stats.originalSize}`);
    console.log(`${details.name}: ${details.stats.minifiedSize}`);
  }))
  .pipe(dest('ui_library'))
  cb();
}

// Compress images and copy from dev/images/ into dev/ui_library/images/:

function copyimages(cb) {
  return src('dev/images/**/*.+(png|jpg|jpeg|gif|svg)')
  .pipe(cache(imagemin({
      interlaced: true
    })))
  .pipe(dest('ui_library/images'))
  cb();
}

// Copy the minified css to the place it actually needs to go in order to function
function copyCSS(cb) {
  return src('ui_library/css/main2.min.css')
    .pipe(dest('static_src/stylesheets'));
  cb();
}

// Copy font files from dev/fonts/ into dev/ui_library/fonts/:

function fonts(cb) {
  return src('dev/fonts/**/*')
  .pipe(dest('ui_library/fonts'))
  cb();
}

// Delete ui_library directory at start of build process:

function clean(cb) {
  return del('ui_library');
  cb();
}

// Lint Sass:

function scsslint(cb) {
  return src(['dev/scss/*.scss', '!dev/scss/vendor/*.scss'])
  .pipe(stylelint({
    reporters: [
      {formatter: 'string', console: true}
    ]
  }));
  cb();
}

function scsslint_legacy(cb) {
  return src(['dev/legacy-scss/*.scss', '!dev/legacy-scss/vendor/*.scss'])
  .pipe(stylelint({
    reporters: [
      {formatter: 'string', console: true}
    ]
  }));
  cb();
}



// Lint JavaScript:

function jslint(cb) {
  return src(['dev/js/**/*.js', '!dev/js/vendor/*.js'])
  .pipe(jshint())
  .pipe(jshint.reporter('default'))
  cb();
}

// Upload ui_library build to GitHub Pages:

function githubpages(cb) {
  return src('./ui_library/**/*')
  .pipe(ghPages())
  cb();
}

// Run "gulp modernizr" to build a custom modernizr file based off of classes found in CSS:

function runmodernizr(cb) {
  return src('dev/css/main2.css') // where modernizr will look for classes
  .pipe(modernizr({
    options: ['setClasses'],
    dest: 'dev/js/modernizr-custombuild.js'
  }))
  cb();
}
