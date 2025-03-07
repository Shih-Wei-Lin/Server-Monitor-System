# version_updates.py


updates_data = [
    {
        "version": "1.2.9",
        "release_date": "2024-12-04",
        "features": [
            {"description": "Modify internal code"},
            {"description": "Change unit converter"},
            {"description": "Modify UI"},
        ],
    },
    {
        "version": "1.2.8",
        "release_date": "2024-09-23",
        "features": [
            {
                "description": "Add the function of directing to git & filestation in the sidebar"
            },
        ],
    },
    {
        "version": "1.2.7",
        "release_date": "2024-09-20",
        "features": [
            {"description": "Fix calculator errors"},
            {"description": "Fixed display issue in light mode"},
        ],
    },
    {
        "version": "1.2.6",
        "release_date": "2024-09-19",
        "features": [
            {"description": "Added useful calculator page"},
            {
                "description": "Add the function of directing to SIPI library in the sidebar"
            },
            {"description": "Modularize the original code into utils.py, db_utils.py"},
        ],
    },
    {
        "version": "1.2.5",
        "release_date": "2024-09-02",
        "features": [
            {"description": "Modify bug for update server usage data's source code."},
        ],
    },
    {
        "version": "1.2.4",
        "release_date": "2024-08-30",
        "features": [
            {
                "description": "Modify the statistics page to not connect when there is no data when the server is shut down.(Statistics)"
            },
            {
                "description": "Change the user and account display interface to make the interface more tidy(Server Usage)"
            },
            {
                "description": "When the same user logs in to the server with different accounts at the same time, it will be displayed as a duplicate user. Please do not log out of other people's accounts at will.(Server Usage)"
            },
        ],
    },
    {
        "version": "1.2.3",
        "release_date": "2024-08-29",
        "features": [
            {
                "description": "Improve viewing experience on light backgrounds(Server Usage& Statistics)"
            },
        ],
    },
    {
        "version": "1.2.2",
        "release_date": "2024-08-28",
        "features": [
            {"description": "Improve Version Update resource code"},
        ],
    },
    {
        "version": "1.2.1",
        "release_date": "2024-08-27",
        "features": [
            {
                "description": "Change the display logic of the statistics page to display all server CPU resources"
            },
            {
                "description": "You can decide to display information by clicking the label"
            },
            {"description": "Fix bug that won't update automatically"},
        ],
    },
    {
        "version": "1.1.0",
        "release_date": "2024-08-26",
        "features": [
            {"description": "Change Account and User display interface"},
            {"description": "Add version_update page"},
        ],
    },
    {
        "version": "1.0.0",
        "release_date": "2024-08-20",
        "features": [{"description": "Initial release"}],
    },
]


def display_version_updates(st):
    for update in updates_data:
        st.subheader(f"Version {update['version']} - {update['release_date']}")
        for i, feature in enumerate(update["features"], start=1):
            st.write(f"{i}. {feature['description']}")
