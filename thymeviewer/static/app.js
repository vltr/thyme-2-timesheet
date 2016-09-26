angular.module("myApp", ["ngTable"]);

(function() {
    "use strict";

    angular.module("myApp").controller("demoController", demoController);
    demoController.$inject = ["NgTableParams", "$http", "$q"];

    function demoController(NgTableParams, $http, $q) {
        var self = this;

        self.tableParams = new NgTableParams({}, {
            getData: function(params) {
                var d = $q.defer();
                $http({
                    method: 'GET',
                    url: '/entries/'
                }).then(function (response) {
                    params.total(response.data.total);
                    d.resolve(response.data.result);
                }, function errorCallback(response) {
                    console.log(response);
                });
                return d.promise;
            }
        });

        self.cancel = cancel;
        self.del = del;
        self.save = save;

        function cancel(row, rowForm) {
            var originalRow = resetRow(row, rowForm);
            angular.extend(row, originalRow);
        }

        function del(row) {
            _.remove(self.tableParams.settings().dataset, function(item) {
                return row === item;
            });

            self.tableParams.reload().then(function(data) {
                if (data.length === 0 && self.tableParams.total() > 0) {
                    self.tableParams.page(self.tableParams.page() - 1);
                    self.tableParams.reload();
                }
            });
        }

        function resetRow(row, rowForm) {
            row.isEditing = false;
            rowForm.$setPristine();
            self.tableTracker.untrack(row);
            return _.findWhere(originalData, function(r){
                return r.id === row.id;
            });
        }

        function save(row, rowForm) {
            var originalRow = resetRow(row, rowForm);
            angular.extend(originalRow, row);
        }
    }
})();

(function() {
    "use strict";

    angular.module("myApp").run(configureDefaults);
    configureDefaults.$inject = ["ngTableDefaults"];

    function configureDefaults(ngTableDefaults) {
        ngTableDefaults.params.count = 900;
        ngTableDefaults.settings.counts = [];
    }
})();
