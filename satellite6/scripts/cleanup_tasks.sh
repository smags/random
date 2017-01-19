#!/bin/bash
VERBOSE=false
AFTER=1d

# Repositories
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Repository::Sync' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Repository::CapsuleGenerateAndSync' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Repository::MetadataGenerate' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Repository::Create' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Repository::Destroy' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::RepositorySet::ScanCdn' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::RepositorySet::EnableRepository' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::RepositorySet::DisableRepository' VERBOSE=${VERBOSE}

# Hosts
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::UploadPackageProfile' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::Erratum::ApplicableErrataInstall' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::Hypervisors' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::GenerateApplicability' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::Update' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::Destroy' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::AttachSubscriptions' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::RecalculateErrataStatus' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::Register' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Host::Unregister' VERBOSE=${VERBOSE}

# Content Views
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::ContentViewVersion::Destroy' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::ContentView::Promote' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::ContentView::CapsuleGenerateAndSync' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::ContentView::Publish' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::ContentView::Update' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::ContentView::IncrementalUpdates' VERBOSE=${VERBOSE}

# all other tasks
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::BulkAction' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Provider::ManifestRefresh' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::CapsuleContent::Sync' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Product::Destroy' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::SyncPlan::AddProducts' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Product::Create' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::Organization::Create' VERBOSE=${VERBOSE}

# Doesn't work
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Katello::EventQueue::Monitor' VERBOSE=${VERBOSE}
foreman-rake foreman_tasks:cleanup AFTER=${AFTER} TASK_SEARCH='Actions::Candlepin::ListenOnCandlepinEvents' VERBOSE=${VERBOSE}

