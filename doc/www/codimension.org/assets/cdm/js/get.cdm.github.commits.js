$(function() {
    $('#github-commits-cdm').githubInfoWidget(
        { user: 'SergeySatskiy', repo: 'codimension', branch: 'master', last: 5, limitMessageTo: 40 });
});
$(function() {
    $('#github-commits-pyparser').githubInfoWidget(
        { user: 'SergeySatskiy', repo: 'cdm-pythonparser', branch: 'master', last: 5, limitMessageTo: 40 });
});
 $(function() {
    $('#github-commits-flowparser').githubInfoWidget(
        { user: 'SergeySatskiy', repo: 'cdm-flowparser', branch: 'master', last: 5, limitMessageTo: 40 });
});
