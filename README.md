# behave-parallel-runner
#### Custom Behave Parallel Feature Runner implementation
This library provides functionality to run Behave features in parallel.

The amount of features that will run in parallel is determined by **_MAX_WORKERS_**, set to the default value when not specified.
    



Command line usage
-------
    behave_parallel_runner <tag_args> <feature_args>


Accepted args
-------
#### \<tag_args\>
* --tags=some_tag (same as 'behave' command)

#### \<feature_args\>
* Single path to a features directory
* Single path to a feature file
* Multiple paths to different feature files



Usage examples
-------
##### Scenarios tagged as _@smoke_ in a single path to a features directory
```behave_parallel_runner --tags=smoke ui_tests/admin/features```

##### Scenarios tagged as _@prod_ in a single feature
```behave_parallel_runner --tags=prod ui_tests/admin/features/health.feature```

##### Scenarios tagged as _@prod_ and _@smoke_ in two features
```behave_parallel_runner --tags=prod --tags=smoke ui_tests/admin/features/health.feature ui_tests/admin/features/apigee.feature```
