/**
 * jQuery "Two-Button" Formset
 * @author Andy Mardesich (Andy DOT Mardesich AT ucop DOT edu)
 * @requires jQuery 1.2.6 or later
 *
 * Copyright (c) 2016, Andy Mardesich
 * All rights reserved.
 *
 * Originally based on jQuery Formset 1.3-pre: https://github.com/elo80ka/django-dynamic-formset
 * But this script uses only one add button and one delete button.
 * Does not work with inline formsets.
 */
;(function($) {
    $.fn.formset = function (opts)
    {
        var options = $.extend({}, $.fn.formset.defaults, opts),
            addButton = $('#' + options.auto_id + options.addCssId),
            delButton = $('#' + options.auto_id + options.deleteCssId),
            flatExtraClasses = options.extraClasses.join(' '),
            totalForms = $('#' + options.auto_id + options.prefix + '-TOTAL_FORMS'),
            maxForms = $('#' + options.auto_id  + options.prefix + '-MAX_NUM_FORMS'),
            minForms = $('#' + options.auto_id  + options.prefix + '-MIN_NUM_FORMS'),
            childElementSelector = 'input,select,textarea,label,div,span',
            $$ = $(this),

            applyExtraClasses = function(row, ndx) {
                if (options.extraClasses) {
                    row.removeClass(flatExtraClasses);
                    row.addClass(options.extraClasses[ndx % options.extraClasses.length]);
                }
            },

            updateElementIndex = function(elem, prefix, ndx) {
                var idRegex = new RegExp(prefix + '-(\\d+|__prefix__)-'),
                    replacement = prefix + '-' + ndx + '-';
                if (elem.attr("for")) elem.attr("for", elem.attr("for").replace(idRegex, replacement));
                if (elem.attr('id')) elem.attr('id', elem.attr('id').replace(idRegex, replacement));
                if (elem.attr('name')) elem.attr('name', elem.attr('name').replace(idRegex, replacement));
            },

            hasChildElements = function(row) {
                return row.find(childElementSelector).length > 0;
            },

            clearField = function() {
                var elem = $(this);
                // If this is a checkbox or radiobutton, uncheck it.
                // http://stackoverflow.com/questions/6364289/clear-form-fields-with-jquery
                if (elem.is('input:checkbox') || elem.is('input:radio')) {
                    elem.attr('checked', false);
                } else {
                    elem.val('');
                }
            },

            /**
            * Indicates whether add button can be displayed - when total forms < max forms
            */
            showAddButton = function() {
                return maxForms.length === 0 ||   // For Django versions pre 1.2
                    (maxForms.val() === '' || (maxForms.val() - totalForms.val() > 0));
            },

            /**
            * Indicates whether delete button can be displayed - when total forms > min forms
            */
            showDeleteButton = function() {
                return minForms.length === 0 ||   // For Django versions pre 1.7
                    (minForms.val() === '' || (totalForms.val() - minForms.val() > 0));
            };

        $$.each(function(i) {
            var row = $(this);
            if (hasChildElements(row)) {
                row.addClass(options.formCssClass);
                if (row.is(':visible')) {
                    applyExtraClasses(row, i);
                }
            }
        });

        if ($$.length) {
            var template,
                myid = $(this).closest('.fieldset-stacked').attr('id');  // for testing
            if (options.formTemplate) {
                // If a form template was specified, we'll clone it to generate new form instances:
                template = (options.formTemplate instanceof $) ? options.formTemplate : $(options.formTemplate);
                template.removeAttr('id').addClass(options.formCssClass + ' formset-custom-template');
                template.find(childElementSelector).each(function() {
                    updateElementIndex($(this), options.prefix, '__prefix__');
                });
            } else {
                // Use the last form in the formset; this works much better if you've got
                // extra (>= 1) forms:
                template = $('.' + options.formCssClass + ':last').clone(true).removeAttr('id');
                // Clear all cloned fields, except those the user wants to keep:
                template.find(childElementSelector).not(options.keepFieldValues).each(function() {
                    var elem = $(this);
                    // If this is a checkbox or radiobutton, uncheck it.
                    // http://stackoverflow.com/questions/6364289/clear-form-fields-with-jquery
                    if (elem.is('input:checkbox') || elem.is('input:radio')) {
                        elem.attr('checked', false);
                    } else {
                        elem.val('');
                    }
                });
            }
            // FIXME: Perhaps using $.data would be a better idea?
            options.formTemplate = template;

            if (!showAddButton()) addButton.hide();
        }

        addButton.click(function() {
            var formCount = parseInt(totalForms.val()),
                row = options.formTemplate.clone(true).removeClass('formset-custom-template');
            applyExtraClasses(row, formCount);
            row.insertAfter($$.filter(':last')).show();
            row.find(childElementSelector).each(function() {
                updateElementIndex($(this), options.prefix, formCount);
            });
            totalForms.val(formCount + 1);
            console.log("id=%s, totalForms = %s", myid, totalForms.val());
            // Check if we've exceeded the maximum allowed number of forms:
            if (!showAddButton()) $(this).hide();
            if (delButton.is(':hidden') && showDeleteButton()) delButton.show();
            return false;
        });

        delButton.click(function() {
            if (confirm("Please confirm you want to remove last item.")) {
                var lastRow = $$.filter(':last');
                if (totalForms.val() == 1) {
                    // Just erase values (don't remove form completely)
                    lastRow.find(childElementSelector).not(options.keepFieldValues).each(function() {
                        var elem = $(this);
                        // If this is a checkbox or radiobutton, uncheck it.
                        // http://stackoverflow.com/questions/6364289/clear-form-fields-with-jquery
                        if (elem.is('input:checkbox') || elem.is('input:radio')) {
                            elem.attr('checked', false);
                        } else {
                            elem.val('');
                        }
                    });
                } else {
                    lastRow.remove();
                    // Update the TOTAL_FORMS count:
                    var forms = $('.' + options.formCssClass).not('.formset-custom-template');
                    totalForms.val(forms.length);
                    // Check if we've reached the minimum number of forms
                    if (!showDeleteButton()) $(this).hide();
                    // Check if we need to show the add button:
                    if (addButton.is(':hidden') && showAddButton()) addButton.show();
                }
                console.log("id=%s, totalForms = %s", myid, totalForms.val());
            }
            return false;
        });

        return $$;

    };

    /* Setup plugin defaults */
    $.fn.formset.defaults = {
        auto_id: 'id_',                     // prepended string on field's id attribute
        prefix: 'form',                  // The form prefix for your django formset
        formTemplate: null,              // The jQuery selection cloned to generate new form instances
        formCssClass: 'dynamic-form',    // CSS class applied to each form in a formset
        extraClasses: [],                // Additional CSS classes, which will be applied to each form in turn
        keepFieldValues: ''             // jQuery selector for fields whose values should be kept when the form is cloned
    };
})(jQuery);

