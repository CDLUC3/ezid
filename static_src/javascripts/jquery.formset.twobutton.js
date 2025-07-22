/*
 * Copyright©2016-2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
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
            childElementSelector = 'input,select,textarea,label,div,span,details',
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

            clearInvalidReqd = function(elem) {
                if (elem.attr('class')) {
                    var rx_invalid = /(.+)--invalid/,
                        rx_reqd = /(.+)-required/,
                        cNames = elem.attr('class').toString().split(' ');
                    $.each(cNames, function (i, className) {
                        var match_inv = rx_invalid.exec(className);
                        if (match_inv) {
                            elem.removeClass(className).addClass(match_inv[1]);
                        }
                        var match_reqd = rx_reqd.exec(className);
                        if (match_reqd) {
                            elem.removeClass(className).addClass(match_reqd[1]);
                        }
                    });
                }
            },

            hasChildElements = function(row) {
                return row.find(childElementSelector).length > 0;
            },

            clearField = function(elem) {
                elem = $(elem);
                // console.log('Clearing field:', elem.attr('name') || elem.attr('id'));

                if (elem.is('input:checkbox') || elem.is('input:radio')) {
                    elem.prop('checked', false);
                } else {
                    elem.val('');
                }
            },

            getLastRow = function() {
                return $$.parent().children('.' + options.formCssClass + ':last');
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
                    clearField(this);
                });
            }
            // FIXME: Perhaps using $.data would be a better idea?
            options.formTemplate = template;

            if (!showAddButton()) addButton.hide();
        }

        addButton.click(function() {
            var formCount = parseInt(totalForms.val()),
                row = options.formTemplate.clone(true).removeClass('formset-custom-template'),
                lastRow = getLastRow();
            applyExtraClasses(row, formCount);
            row.insertAfter(lastRow).show();
            row.find(childElementSelector).each(function() {
                updateElementIndex($(this), options.prefix, formCount);
                clearInvalidReqd($(this));
            });
            row.find(':input').each(function() {
                clearField(this);
            });
            // Generate any links to help content from newly created elements
            $.getScript("/static/javascripts/help_box_.js");
            totalForms.val(formCount + 1);
            console.log("id=%s, totalForms = %s", myid, totalForms.val());
            // Check if we've exceeded the maximum allowed number of forms:
            if (!showAddButton()) $(this).hide();
            if (delButton.is(':hidden') && showDeleteButton()) delButton.show();
            return false;
        });

        delButton.click(function() {
            if (confirm("Please confirm you want to remove last item.")) {
                var lastRow = getLastRow();
                if (totalForms.val() == 1) {
                    // Just erase values (don't remove form completely)
                    lastRow.find(childElementSelector).not(options.keepFieldValues).each(function() {
                        var elem = $(this);
                        if (elem.is('details')) {
                            elem.removeAttr('open');
                        } else {
                            clearField(elem);
                        }
                    });
                } else {
                    lastRow.remove();
                    // Update the TOTAL_FORMS count:
                    var forms = $$.parent().children('.' + options.formCssClass).not('.formset-custom-template');
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
        extraClasses: ['vertical-buffer-sm'],  // Additional CSS classes, which will be applied to each form in turn
        keepFieldValues: ''             // jQuery selector for fields whose values should be kept when the form is cloned
    };
})(jQuery);
