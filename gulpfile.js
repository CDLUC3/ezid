/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

// ##### Gulp Tasks #####

var { src, dest, watch, series, parallel } = require('gulp');
var path = require('path');
var sass = require('gulp-sass')(require('sass'));
var autoprefixer = require('autoprefixer');
var browserSync = require('browser-sync');
var server = browserSync.create();
var through2 = require('through2');
var useref = require('gulp-useref');
var uglify = require('gulp-uglify');
var gulpIf = require('gulp-if');
var cleanCSS = require('gulp-clean-css');
var deleteAsync = require('del').deleteAsync;
var modernizr = require('gulp-modernizr');
var stylelint = require('stylelint');
var jshint = require('gulp-jshint');
var lbInclude = require('gulp-lb-include');
var ssi = require('browsersync-ssi');
var postcss = require('gulp-postcss');
var assets = require('postcss-assets');
var ghPages = require('gulp-gh-pages');
var sharp = require('sharp');
var optimizeSvg = require('svgo').optimize;

// Public Tasks:

exports.default = parallel(scss, start, watcher);

// exports.build = series(clean, fonts, scsslint_legacy, scsslint, jslint, scss_legacy, scss, assemble, minifyCss, copyimages, fonts);
exports.build = series(clean, fonts, jslint, scss_legacy, scss, assemble, minifyCss, copyimages, fonts, copyCSS, copyJS);

exports.upload = githubpages;

exports.modernizr = runmodernizr;

exports.scsslint_legacy = scsslint_legacy;

// Process scss to css, add sourcemaps, inline font & image files into css:

sass.compiler = require('sass');

// Temporary deprecation-noise reduction while legacy SCSS is still being modernized.
var dartSassOptions = {
  quietDeps: true,
  silenceDeprecations: [
    'legacy-js-api',
    'import',
    'global-builtin',
    'color-functions',
    'slash-div',
    'if-function'
  ]
};

function scss() {
  return src('dev/scss/*.scss', { sourcemaps: true })
  .pipe(sass(dartSassOptions).on('error', sass.logError))
  .pipe(postcss([autoprefixer({
    overrideBrowserslist: ['last 2 versions']
  }), assets({
    loadPaths: ['fonts/', 'images/']
  })]))
  .pipe(dest('dev/css', { sourcemaps: 'sourcemaps' }))
  .pipe(browserSync.stream());
}

function scss_legacy() {
  return src('dev/legacy-scss/*.scss', { sourcemaps: true })
  .pipe(sass(dartSassOptions).on('error', sass.logError))
  .pipe(postcss([autoprefixer({
    overrideBrowserslist: ['last 2 versions']
  })]))
  .pipe(dest('dev/legacy-scss/css', { sourcemaps: 'sourcemaps' }))
  .pipe(browserSync.stream());
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

function assemble() {
  return src(['dev/**/*.html', '!dev/includes/*', 'dev/css/*.css'])
  .pipe(gulpIf('*.js', uglify()))
  .pipe(useref())
  .pipe(lbInclude()) // parse <!--#include file="" --> statements
  .pipe(dest('ui_library'))
}

function minifyCss() {
  return src(['dev/css/*.css'])
  .pipe(cleanCSS({debug: true, level: 2}, (details) => {
    console.log(`${details.name}: ${details.stats.originalSize}`);
    console.log(`${details.name}: ${details.stats.minifiedSize}`);
  }))
  .pipe(dest('ui_library'))
}

// Compress images and copy from dev/images/ into dev/ui_library/images/:

function copyimages() {
  return src('dev/images/**/*.+(png|jpg|jpeg|gif|svg)')
    .pipe(through2.obj(function (file, enc, cb) {
      if (file.isNull()) {
        cb(null, file);
        return;
      }

      if (file.isStream()) {
        cb(new Error('Streaming images are not supported by copyimages.'));
        return;
      }

      var extension = path.extname(file.path).toLowerCase();

      if (extension === '.svg') {
        try {
          var result = optimizeSvg(file.contents.toString(enc || 'utf8'), {
            path: file.path,
            multipass: true,
            plugins: [
              {
                name: 'preset-default'
              }
            ]
          });

          file.contents = Buffer.from(result.data);
          cb(null, file);
        } catch (error) {
          cb(error);
        }

        return;
      }

      if (extension === '.png' || extension === '.jpg' || extension === '.jpeg') {
        sharp(file.contents)
          .rotate()
          [extension === '.png' ? 'png' : 'jpeg'](extension === '.png'
            ? {
              compressionLevel: 9,
              progressive: true
            }
            : {
              mozjpeg: true,
              quality: 82,
              progressive: true
            })
          .toBuffer()
          .then(function (buffer) {
            file.contents = buffer;
            cb(null, file);
          })
          .catch(function (error) {
            if (error && /unsupported image format/i.test(error.message || '')) {
              console.warn('Skipping optimization for unsupported image format: ' + file.relative);
              cb(null, file);
              return;
            }

            cb(error);
          });

        return;
      }

      cb(null, file);
    }))
    .pipe(dest('ui_library/images'));
}

// Copy the minified css to the place it actually needs to go in order to function
function copyCSS() {
  return src('ui_library/css/main2.min.css')
    .pipe(dest('static_src/stylesheets'));
}

// Copy the minified js to the place it actually needs to go in order to function
function copyJS() {
  return src('ui_library/js/main2.min.js')
    .pipe(dest('static_src/javascripts'));
}

// Copy font files from dev/fonts/ into dev/ui_library/fonts/:

function fonts() {
  return src('dev/fonts/**/*')
  .pipe(dest('ui_library/fonts'))
}

// Delete ui_library directory at start of build process:

function clean() {
  return deleteAsync(['ui_library']);
}

// Lint Sass:

function scsslint() {
  return src(['dev/scss/*.scss', '!dev/scss/vendor/*.scss'])
  .pipe(stylelint({
    reporters: [
      {formatter: 'string', console: true}
    ]
  }));
}

function scsslint_legacy() {
  return src(['dev/legacy-scss/*.scss', '!dev/legacy-scss/vendor/*.scss'])
  .pipe(stylelint({
    reporters: [
      {formatter: 'string', console: true}
    ]
  }));
}



// Lint JavaScript:

function jslint() {
  return src(['dev/js/**/*.js', '!dev/js/vendor/*.js'])
  .pipe(jshint({ esversion: 6 }))
  .pipe(jshint.reporter('default'))
}

// Upload ui_library build to GitHub Pages:

function githubpages() {
  return src('./ui_library/**/*')
  .pipe(ghPages())
}

// Run "gulp modernizr" to build a custom modernizr file based off of classes found in CSS:

function runmodernizr() {
  return src('dev/css/main2.css') // where modernizr will look for classes
  .pipe(modernizr({
    options: ['setClasses'],
    dest: 'dev/js/modernizr-custombuild.js'
  }))
}
