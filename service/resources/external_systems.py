"""Mapping and configuration for external systems"""

MAP = {
    "dbi":{
        "type": "csv",
        "ftp_server_var": "DBI_FTP_SERVER",
        "ftp_username_var": "DBI_FTP_USER",
        "ftp_password_var": "DBI_FTP_PASSWD",
        "template": [
            {"name": "Own the property", "id": "do_you_own_the_property"},
            {"name": "Build ADU myself", "id": "i_am_building_myself"},
            {"name": "First name", "id": "first_name"},
            {"name": "Last name", "id": "last_name"},
            {"name": "Relationship to owner", "id": "relationship_to_owner"},
            {"name": "CA license number", "id": "ca_license_number"},
            {"name": "License expiration date", "id": "license_expiration_date"},
            {"name": "Your organization name", "id": "name_of_organization"},
            {"name": "Mailing address 1", "id": "non_owner_address_1"},
            {"name": "Mailing address 2", "id": "non_owner_address_2"},
            {"name": "Mailing address City", "id": "non_owner_city"},
            {"name": "Mailing address State", "id": "non_owner_state"},
            {"name": "Mailing address Zip", "id": "non_owner_zip"},
            {"name": "Phone", "id": "non_owner_phone_number"},
            {"name": "Email", "id": "non_owner_email"},
            {"name": "Who owns property", "id": "who_owns_property"},
            {"name": "Name of Organization", "id": "owner_name_org"},
            {"name": "Owner's first name", "id": "owners_first_name"},
            {"name": "Owner's last name", "id": "owners_last_name"},
            {"name": "Owner's phone number", "id": "owners_phone_number"},
            {"name": "Owner's email", "id": "owners_email_address"},
            {"name": "Owner Mailing Address 1", "id": "owners_address_1"},
            {"name": "Owner Mailing Address 2", "id": "owners_address_2"},
            {"name": "Owner Mailing Address City", "id": "owners_city"},
            {"name": "Owner Mailing Address State", "id": "owners_state"},
            {"name": "Owner Mailing Address Zip", "id": "owners_zip"},
            {"name": "Same address as ADU project", "id": "also_address"},
            {"name": "Project Address line 1", "id": "project_address_1"},
            {"name": "Project Address line 2", "id": "project_address_2"},
            {"name": "Project Address Zip", "id": "project_zip"},
            {"name": "Block number", "id": "block"},
            {"name": "Lot number", "id": "lot"},
            {"name": "Current building use codes", "id": "building_current_uses"},
            {"name": "Unlisted building use codes", "id": "building_codes_not_listed"},
            {"name": "Proposed codes", "id": "proposed_codes"},
            {"name": "Unlisted proposed codes", "id": "proposed_codes_not_listed"},
            {"name": "Occupancy codes", "id": "property_currrent_occupancy_codes"},
            {"name": "Rest of current occupancy codes", "id": "rest_current_occupancy_codes"},
            {"name": "Will occupancy change", "id": "occupancy_change_yn"},
            {"name": "Proposed occupancy codes", "id": "proposed_occupancy_codes"},
            {"name": "Rest of proposed occupancy codes", "id": "rest_proposed_occupancy_codes"},
            {"name": "Construction type", "id": "type_of_construction"},
            {"name": "Estimated cost", "id": "est_cost"},
            {"name": "Excavation area", "id": "excavation_area"},
            {"name": "Excavation volumn", "id": "excavation_volume"},
            {"name": "Disturbance depth", "id": "depth_disturb"},
            {"name": "Construction impact", "id": "work_involve_checkboxes"},
            {"name": "Is adding height", "id": "add_height"},
            {"name": "New height", "id": "new_height"},
            {"name": "Is adding horizontal extension", "id": "adding_deck"},
            {"name": "New ground floor area", "id": "new_ground_floor"},
            {"name": "Is Maher area", "id": "maher_area"},
            {"name": "Is removing housing services", "id": "remove_housing_services"},
            {"name": "Is residential area changed", "id": "change_after_adu_2"},
            {"name": "Proposed residential area", "id": "proposed_residential_space"},
            {"name": "Existing dwelling units", "id": "existing_dwelling_units"},
            {"name": "Proposed dwelling units", "id": "proposed_dwelling_units"},
            {"name": "Current number buildings", "id": "current_number_buildings"},
            {"name": "Is number buildings changed", "id": "change_after_adu_6"},
            {"name": "Proposed number buildings", "id": "proposed_number_buildings"},
            {"name": "Current number stories", "id": "current_number_stories"},
            {"name": "Is number stories changed", "id": "change_after_adu_7"},
            {"name": "Proposed number stories", "id": "proposed_stories"},
            {"name": "Current number basements or cellars", "id": "basements_cellars"},
            {"name": "Is number basements or cellars changed", "id": "change_after_adu_8"},
            {"name": "Proposed number basements or cellars", "id": "proposed_basements_cellars"},
            {"name": "Has fire sprinklers", "id": "fire_sprinklers_yn"},
            {"name": "Sprinkler coverage", "id": "sprinklers_cover"},
            {"name": "Has fire alarms", "id": "fire_alarms_yn"},
            {"name": "Alarm coverage", "id": "rooms_alarms_cover"},
            {"name": "Workers comp", "id": "workers_comp"},
            {"name": "Insurance carrier", "id": "name_insurance_carrier"},
            {"name": "Policy number", "id": "policy_number"},
            {"name": "Seismic retrofit permit", "id": "seismic_yn"},
            {"name": "Seismic retrofit permit number", "id": "seismic_retrofitting_number"},
            {"name": "Seismic strengthening", "id": "seismic_strengthening_yn"},
            {"name": "Seismic strengthening permit number", "id": "seismic_strengthening_number"},
            {"name": "Follows ADU ordinances", "id": "follow_ordinances"},
            {"name": "Planning additional work", "id": "additional_work_yn"},
            {"name": "Additional work description", "id": "additional_work_text"},
            {"name": "Declared true and correct", "id": "identity_checkboxes_1"},
            {
                "name": "Will comply with permit, laws, and ordinances",
                "id": "identity_checkboxes_2"
            },
            {"name": "Have workers comp certificate", "id": "comp_1"},
            {"name": "Have workers comp insurance", "id": "comp_2"},
            {"name": "Work costs $100 or less", "id": "comp_3"},
            {"name": "CA workers comp inapplicable", "id": "comp_4"},
            {"name": "Will hire contractor who complies with CA workers comp", "id": "comp_5"},
            {"name": "Understand and agree to unlicensed workers page", "id": "attestation_1"},
            {"name": "Understand and agree to owners-builders info page", "id": "attestation_2"},
            {
                "name": "Understand and agree to owners-builders declaration and agreement page",
                "id": "attestation_3"
            },
            {"name": "Num ADUs", "id": "current_num_adu"},
            {
                "type": "grouping",
                "count": 15,
                "template": [
                    {"name": "ADU %#% type", "id": "current_unit_type_adu_%#%"},
                    {"name": "ADU %#% square footage", "id": "current_sq_ft_adu_%#%"},
                    {"name": "ADU %#% ordinance", "id": "current_ordinance_adu_%#%"}
                ]
            }
        ]
    },
    # "fire": {
    #     "type": "api",
    #     "env_var": "FIRE_SYSTEM_URL",
    #     "template": {
    #         "block": "",
    #         "lot": "",
    #         "job_size": "est_cost",
    #         "floors": "stories",
    #         "occupant_type": "property_current_occupancy_codes",
    #         "contractor": "name_of_organization"
    #     }
    # },
    # "planning": {
    #     "type": "api",
    #     "env_var": "PLANNING_SYSTEM_URL",
    #     "template": {
    #         "name": "planning template"
    #     }
    # }
}
