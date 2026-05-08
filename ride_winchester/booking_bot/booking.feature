Feature: Winchester CTC Ride Booking

  Scenario: Log in and filter for Friday rides
    Given I am on the Winchester CTC login page
    When I log in with username "krgough@gmail.com" and password "Fulmar99"
    And I navigate to the rides list
    And I select the "Friday" filter
    Then I should see the Friday rides available