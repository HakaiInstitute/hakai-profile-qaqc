def hakai_ctd_profile_parameters():
    # QC configuration
    # This configuration is used to call the corresponding method in the ioos_qc library
    # See documentation for description of each test and its inputs:
    #   https://ioos.github.io/ioos_qc/api/ioos_qc.html#module-ioos_qc.qartod
    # TODO this should be stored in a json file I think instead.
    # Define all the tests to apply to each variables
    qc_config = {
        "position": {
            "qartod": {
                "location_test": {
                    "bbox": [-180, -90, 180, 90],
                    "range": 3000
                },
                "aggregate": {}
            }
        },
        "pressure": {
            "qartod": {
                "gross_range_test": {
                    "suspect_span": [0, 12000],
                    "fail_span": [0, 12000],
                    "maximum_suspect_depth_ratio": 1.05,
                    "maximum_fail_depth_ratio": 1.1
                },
                "aggregate": {}
            }

        },
        "depth": {
            "qartod": {
                "gross_range_test": {
                    "suspect_span": [0, 12000],
                    "fail_span": [0, 12000],
                    "maximum_suspect_depth_ratio": 1.05,
                    "maximum_fail_depth_ratio": 1.1
                },
                "aggregate": {}
            }
        },
        'dissolved_oxygen_ml_l': {
            'qartod': {
                "gross_range_test": {
                    "fail_span": [0, 12],
                    "suspect_span": [1, 10]
                },
                "rate_of_change_test": {
                    "threshold": 1
                },
                "spike_test": {
                    "suspect_threshold": 0.5,
                    "fail_threshold": 1
                },
                "attenuated_signal_test": {
                    "suspect_threshold": 0.5,
                    "fail_threshold": 0.2,
                    "check_type": "range"
                },
                "aggregate": {}
            }
        },
        'rinko_do_ml_l': {
            'qartod': {
                "gross_range_test": {
                    "fail_span": [0, 12],
                    "suspect_span": [1, 10]
                },
                "rate_of_change_test": {
                    "threshold": 1
                },
                "spike_test": {
                    "suspect_threshold": 0.5,
                    "fail_threshold": 1
                },
                "attenuated_signal_test": {
                    "suspect_threshold": 0.5,
                    "fail_threshold": 0.2,
                    "check_type": "range"
                },
                "aggregate": {}
            }
        },
        "turbidity": {
            "qartod": {
                "gross_range_test": {
                    "fail_span": [-0.1, 10000],
                    "suspect_span": [0, 1000]
                },
                "attenuated_signal_test": {
                    "suspect_threshold": 0.1,
                    "fail_threshold": 0.02,
                    "check_type": "std"
                },
                "aggregate": {}
            }
        },
        "c_star_at": {
            "qartod": {
                "attenuated_signal_test": {
                    "suspect_threshold": 0.002,
                    "fail_threshold": 0.0001,
                    "check_type": "range"
                },
                "spike_test": {
                    "suspect_threshold": 0.05,
                    "fail_threshold": 0.5
                },
                "aggregate": {}
            }

        },
        "par": {
            "qartod": {
                "gross_range_test": {
                    "fail_span": [-0.2, 100000],
                    "suspect_span": [0, 50000]
                },
                "attenuated_signal_test": {
                    "suspect_threshold": 0.05,
                    "fail_threshold": 0.02,
                    "check_type": "std",
                    "test_period": 10,
                    "min_obs": 5,
                    "arg": {"is_profile": True}
                },
                "aggregate": {}
            }
        },
        'salinity': {
            'qartod': {
                "gross_range_test": {
                    "fail_span": [0, 45],
                    "suspect_span": [5, 35]
                },
                "rate_of_change_test": {
                    "threshold": 1
                },
                "spike_test": {
                    "suspect_threshold": 0.5,
                    "fail_threshold": 1
                },
                "aggregate": {}
            }
        },
        'sigma0': {
            'qartod_profile': {
                'density_inversion_test': {
                    'suspect_threshold': -0.005,
                    'fail_threshold': -0.05
                }
            }
        }
    }
    return qc_config
