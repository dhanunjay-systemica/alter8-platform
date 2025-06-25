# Alter8 Platform - Comprehensive Data Model & Design Justification

## 🎯 Data Architecture Strategy

### **Multi-Database Approach Justification**
We're using a **polyglot persistence** strategy with different databases optimized for specific use cases:

1. **PostgreSQL**: Transactional data requiring ACID properties
2. **MongoDB**: Document storage and flexible schemas
3. **Redis**: Caching, sessions, and real-time data
4. **Elasticsearch**: Full-text search and analytics (future)

**Why not a single database?** Different data types have different access patterns, consistency requirements, and performance characteristics.

---

## 🏗️ PostgreSQL Schema Design

### **1. Core User Management**

#### **users table** (Central user registry)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('owner', 'tenant', 'agent', 'field_executive', 'admin', 'super_admin')),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    profile_picture_url TEXT,
    
    -- Account status fields
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified_at TIMESTAMP,
    phone_verified_at TIMESTAMP,
    last_login_at TIMESTAMP,
    
    -- Security fields
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    password_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active, is_verified);
```

**🔍 Design Justifications:**

1. **UUID Primary Keys**: Better for distributed systems, prevents enumeration attacks, allows offline generation
2. **Separate verification flags**: Email and phone verification can happen independently
3. **Security fields**: Failed login attempts and account locking for security
4. **Audit trail**: Track who created/updated records for compliance
5. **Role-based design**: Single role per user for simplicity, can be extended later

#### **user_sessions table** (Session management)
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info JSONB,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(refresh_token_hash);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);
```

**🔍 Why separate session table?**
- Allows multiple active sessions per user (mobile + web)
- Easy session management and revocation
- Device tracking for security
- Redis would lose data on restart

#### **otp_verifications table** (One-time password management)
```sql
CREATE TABLE otp_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    phone VARCHAR(20),
    email VARCHAR(255),
    otp_code VARCHAR(10) NOT NULL,
    otp_type VARCHAR(50) NOT NULL CHECK (otp_type IN ('phone_verification', 'email_verification', 'password_reset', 'login_2fa')),
    attempts INTEGER DEFAULT 0,
    is_used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_otp_user_id ON otp_verifications(user_id);
CREATE INDEX idx_otp_phone ON otp_verifications(phone, otp_type, is_used);
CREATE INDEX idx_otp_email ON otp_verifications(email, otp_type, is_used);
```

**🔍 Why dedicated OTP table?**
- Track OTP attempts to prevent brute force
- Support multiple OTP types with same infrastructure
- Automatic cleanup of expired OTPs
- Audit trail for security compliance

### **2. Role-Specific Profile Extensions**

#### **owner_profiles table**
```sql
CREATE TABLE owner_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Business information
    company_name VARCHAR(255),
    business_type VARCHAR(100), -- individual, company, partnership
    
    -- KYC information
    pan_number VARCHAR(10) UNIQUE,
    aadhar_number VARCHAR(12) UNIQUE,
    gst_number VARCHAR(15),
    
    -- Address information
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    country VARCHAR(100) DEFAULT 'India',
    
    -- Verification status
    kyc_status VARCHAR(20) DEFAULT 'pending' CHECK (kyc_status IN ('pending', 'in_review', 'verified', 'rejected')),
    kyc_documents JSONB, -- Store document references
    verified_at TIMESTAMP,
    verified_by UUID REFERENCES users(id),
    
    -- Financial information
    bank_account_number VARCHAR(20),
    ifsc_code VARCHAR(11),
    bank_name VARCHAR(255),
    account_holder_name VARCHAR(255),
    
    -- Preferences
    preferred_language VARCHAR(10) DEFAULT 'en',
    notification_preferences JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_owner_kyc_status ON owner_profiles(kyc_status);
CREATE INDEX idx_owner_pan ON owner_profiles(pan_number) WHERE pan_number IS NOT NULL;
```

**🔍 Complex Design Decisions:**

1. **JSONB for documents**: Flexible storage for different document types without schema changes
2. **Separate financial info**: Required for rent collection and tax reporting
3. **Verification workflow**: Multi-step KYC process with audit trail
4. **Address normalization**: Structured for search and analytics

#### **agent_profiles table**
```sql
CREATE TABLE agent_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Professional information
    rera_license VARCHAR(50) UNIQUE,
    license_expiry DATE,
    agency_name VARCHAR(255),
    agency_rera_number VARCHAR(50),
    specialization TEXT[], -- Array of specializations like 'residential', 'commercial'
    
    -- Performance metrics
    total_deals_closed INTEGER DEFAULT 0,
    total_commission_earned DECIMAL(15,2) DEFAULT 0,
    average_rating DECIMAL(3,2) DEFAULT 0,
    total_ratings INTEGER DEFAULT 0,
    
    -- Commission structure
    commission_rate DECIMAL(5,2) DEFAULT 2.00, -- Percentage
    commission_type VARCHAR(20) DEFAULT 'percentage' CHECK (commission_type IN ('percentage', 'flat', 'tiered')),
    
    -- Verification and status
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'suspended', 'rejected')),
    verification_documents JSONB,
    verified_at TIMESTAMP,
    verified_by UUID REFERENCES users(id),
    
    -- Working areas (geographic coverage)
    service_areas JSONB, -- Array of {city, state, pincode_ranges}
    
    -- Contact preferences
    preferred_contact_time TIME,
    available_days INTEGER[], -- Array of weekdays (1=Monday, 7=Sunday)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_rera ON agent_profiles(rera_license);
CREATE INDEX idx_agent_verification ON agent_profiles(verification_status);
CREATE INDEX idx_agent_rating ON agent_profiles(average_rating DESC);
```

**🔍 Why complex agent model?**
- **RERA compliance**: Legal requirement in India
- **Performance tracking**: Commission calculation and rating system
- **Geographic coverage**: Agents work in specific areas
- **Flexible commission**: Different agents have different structures

#### **tenant_profiles table**
```sql
CREATE TABLE tenant_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Personal information
    date_of_birth DATE,
    occupation VARCHAR(255),
    employer_name VARCHAR(255),
    work_address TEXT,
    
    -- Financial information
    monthly_income DECIMAL(10,2),
    income_proof_type VARCHAR(50), -- salary_slip, bank_statement, itr
    annual_income DECIMAL(12,2),
    
    -- Identity verification
    aadhar_number VARCHAR(12) UNIQUE,
    pan_number VARCHAR(10),
    
    -- Background check
    background_check_status VARCHAR(20) DEFAULT 'pending' CHECK (background_check_status IN ('pending', 'in_progress', 'passed', 'failed')),
    background_check_report JSONB,
    credit_score INTEGER,
    
    -- Emergency contact
    emergency_contact_name VARCHAR(255),
    emergency_contact_phone VARCHAR(20),
    emergency_contact_relation VARCHAR(100),
    
    -- Rental preferences
    preferred_property_types TEXT[],
    budget_min DECIMAL(10,2),
    budget_max DECIMAL(10,2),
    preferred_locations JSONB,
    
    -- References
    previous_landlord_contact TEXT,
    reference_contacts JSONB, -- Array of reference contacts
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tenant_background ON tenant_profiles(background_check_status);
CREATE INDEX idx_tenant_income ON tenant_profiles(monthly_income);
CREATE INDEX idx_tenant_aadhar ON tenant_profiles(aadhar_number) WHERE aadhar_number IS NOT NULL;
```

**🔍 Why detailed tenant model?**
- **Rental decision factors**: Income, background checks are crucial for landlords
- **Reference system**: Previous landlord references are important in India
- **Preference matching**: Help match tenants with suitable properties
- **Compliance**: Identity verification required by law

### **3. Property Management**

#### **properties table** (Core property data)
```sql
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    listing_agent_id UUID REFERENCES users(id),
    
    -- Basic property information
    title VARCHAR(255) NOT NULL,
    description TEXT,
    property_type VARCHAR(50) NOT NULL CHECK (property_type IN ('apartment', 'house', 'villa', 'commercial', 'plot', 'pg')),
    sub_type VARCHAR(50), -- 1bhk, 2bhk, studio, etc.
    
    -- Location details
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    landmark VARCHAR(255),
    area_name VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    country VARCHAR(100) DEFAULT 'India',
    
    -- Geographic coordinates
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    location_accuracy INTEGER, -- in meters
    
    -- Property specifications
    carpet_area DECIMAL(10,2), -- in sq ft
    built_up_area DECIMAL(10,2),
    super_built_up_area DECIMAL(10,2),
    plot_area DECIMAL(10,2),
    bedrooms INTEGER NOT NULL DEFAULT 0,
    bathrooms DECIMAL(3,1) NOT NULL DEFAULT 0,
    balconies INTEGER DEFAULT 0,
    parking_spaces INTEGER DEFAULT 0,
    floor_number INTEGER,
    total_floors INTEGER,
    
    -- Property details
    furnishing_status VARCHAR(20) DEFAULT 'unfurnished' CHECK (furnishing_status IN ('unfurnished', 'semi_furnished', 'fully_furnished')),
    property_age INTEGER, -- in years
    construction_year INTEGER,
    
    -- Rental information
    monthly_rent DECIMAL(10,2),
    security_deposit DECIMAL(10,2),
    maintenance_charge DECIMAL(10,2),
    brokerage DECIMAL(10,2),
    available_from DATE,
    lease_duration_months INTEGER DEFAULT 12,
    
    -- Amenities (using PostgreSQL array)
    amenities TEXT[],
    
    -- Property status and workflow
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'rented', 'maintenance', 'inactive', 'sold')),
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN ('pending', 'in_progress', 'verified', 'rejected')),
    listing_status VARCHAR(20) DEFAULT 'private' CHECK (listing_status IN ('private', 'public', 'featured')),
    
    -- Visibility and preferences
    is_available BOOLEAN DEFAULT TRUE,
    allow_pets BOOLEAN DEFAULT FALSE,
    preferred_tenant_type VARCHAR(50), -- family, bachelor, company, any
    dietary_preference VARCHAR(50), -- veg_only, non_veg_ok, any
    
    -- SEO and search
    slug VARCHAR(255) UNIQUE,
    meta_title VARCHAR(255),
    meta_description TEXT,
    
    -- Pricing and market data
    market_value DECIMAL(12,2),
    price_per_sqft DECIMAL(10,2),
    
    -- Audit and timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    verified_at TIMESTAMP,
    verified_by UUID REFERENCES users(id)
);

-- Performance indexes
CREATE INDEX idx_properties_owner ON properties(owner_id);
CREATE INDEX idx_properties_agent ON properties(listing_agent_id);
CREATE INDEX idx_properties_location ON properties(city, state, pincode);
CREATE INDEX idx_properties_status ON properties(status, is_available);
CREATE INDEX idx_properties_type ON properties(property_type, sub_type);
CREATE INDEX idx_properties_rent ON properties(monthly_rent) WHERE monthly_rent IS NOT NULL;
CREATE INDEX idx_properties_area ON properties(carpet_area, bedrooms, bathrooms);

-- Geographic index for location-based searches
CREATE INDEX idx_properties_coordinates ON properties USING GIST (point(longitude, latitude));

-- Full-text search index
CREATE INDEX idx_properties_search ON properties USING GIN (to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || area_name));
```

**🔍 Complex Property Design Decisions:**

1. **Multiple area measurements**: Indian real estate uses different area calculations
2. **Geographic indexing**: GIST index for radius-based searches
3. **Flexible amenities**: Array type allows easy filtering without joins
4. **Verification workflow**: Properties go through verification before listing
5. **SEO optimization**: Slug and meta fields for search engine optimization
6. **Cultural preferences**: Dietary and tenant type preferences common in India

#### **property_amenities table** (Normalized amenities for better filtering)
```sql
CREATE TABLE property_amenities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    amenity_type VARCHAR(50) NOT NULL, -- gym, pool, parking, security, etc.
    amenity_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_available BOOLEAN DEFAULT TRUE,
    additional_cost DECIMAL(10,2), -- if amenity has extra cost
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_amenities_property ON property_amenities(property_id);
CREATE INDEX idx_amenities_type ON property_amenities(amenity_type);
```

**🔍 Why separate amenities table?**
- Better filtering and search capabilities
- Track amenity-specific costs
- Easier analytics on popular amenities
- Standardization of amenity names

### **4. Verification and Media Management**

#### **property_verifications table**
```sql
CREATE TABLE property_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id),
    agent_id UUID REFERENCES users(id),
    field_executive_id UUID REFERENCES users(id),
    
    -- Verification details
    verification_type VARCHAR(50) DEFAULT 'standard' CHECK (verification_type IN ('standard', 'premium', 'legal')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'in_progress', 'completed', 'rejected')),
    
    -- Assignment and scheduling
    assigned_at TIMESTAMP,
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Verification data
    verification_report JSONB,
    quality_score INTEGER CHECK (quality_score >= 1 AND quality_score <= 10),
    issues_found TEXT[],
    recommendations TEXT[],
    
    -- Media references
    verification_photos TEXT[], -- URLs to verification photos
    verification_video_url TEXT,
    virtual_tour_url TEXT,
    
    -- Legal verification (if applicable)
    legal_documents_verified BOOLEAN DEFAULT FALSE,
    title_clear BOOLEAN,
    legal_issues TEXT[],
    
    -- Feedback and rating
    agent_rating INTEGER CHECK (agent_rating >= 1 AND agent_rating <= 5),
    executive_rating INTEGER CHECK (executive_rating >= 1 AND executive_rating <= 5),
    feedback TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_verification_property ON property_verifications(property_id);
CREATE INDEX idx_verification_status ON property_verifications(status);
CREATE INDEX idx_verification_executive ON property_verifications(field_executive_id);
```

**🔍 Why complex verification system?**
- **Quality assurance**: Ensures property information accuracy
- **Workflow management**: Track verification process from assignment to completion
- **Performance metrics**: Rate field executives and track quality
- **Legal compliance**: Property title verification important in India

### **5. Tenant and Lease Management**

#### **leases table**
```sql
CREATE TABLE leases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id),
    tenant_id UUID NOT NULL REFERENCES users(id),
    owner_id UUID NOT NULL REFERENCES users(id),
    agent_id UUID REFERENCES users(id),
    
    -- Lease terms
    lease_start_date DATE NOT NULL,
    lease_end_date DATE NOT NULL,
    notice_period_days INTEGER DEFAULT 30,
    renewal_option BOOLEAN DEFAULT TRUE,
    auto_renewal BOOLEAN DEFAULT FALSE,
    
    -- Financial terms
    monthly_rent DECIMAL(10,2) NOT NULL,
    security_deposit DECIMAL(10,2) NOT NULL,
    maintenance_charge DECIMAL(10,2) DEFAULT 0,
    brokerage_amount DECIMAL(10,2) DEFAULT 0,
    
    -- Rent escalation
    annual_rent_increase_percent DECIMAL(5,2) DEFAULT 0,
    next_rent_review_date DATE,
    
    -- Agreement details
    lease_agreement_url TEXT, -- URL to signed agreement
    agreement_type VARCHAR(50) DEFAULT 'standard' CHECK (agreement_type IN ('standard', 'custom', 'legal')),
    special_terms TEXT[],
    
    -- Status and workflow
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'pending_approval', 'active', 'expired', 'terminated', 'renewed')),
    approval_status VARCHAR(20) DEFAULT 'pending' CHECK (approval_status IN ('pending', 'owner_approved', 'tenant_approved', 'fully_approved', 'rejected')),
    
    -- Termination details
    termination_date DATE,
    termination_reason TEXT,
    termination_notice_date DATE,
    early_termination_penalty DECIMAL(10,2),
    
    -- Digital signatures
    owner_signature_url TEXT,
    tenant_signature_url TEXT,
    witness_signature_url TEXT,
    signed_at TIMESTAMP,
    
    -- Audit trail
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_leases_property ON leases(property_id);
CREATE INDEX idx_leases_tenant ON leases(tenant_id);
CREATE INDEX idx_leases_owner ON leases(owner_id);
CREATE INDEX idx_leases_status ON leases(status);
CREATE INDEX idx_leases_dates ON leases(lease_start_date, lease_end_date);
```

**🔍 Complex Lease Design:**
- **Digital signature support**: Legal compliance for digital agreements
- **Approval workflow**: Multi-party approval process
- **Automatic rent escalation**: Built-in rent review mechanism
- **Termination tracking**: Important for security deposit return

#### **rent_payments table**
```sql
CREATE TABLE rent_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id UUID NOT NULL REFERENCES leases(id),
    tenant_id UUID NOT NULL REFERENCES users(id),
    owner_id UUID NOT NULL REFERENCES users(id),
    
    -- Payment details
    payment_period_start DATE NOT NULL,
    payment_period_end DATE NOT NULL,
    due_date DATE NOT NULL,
    amount_due DECIMAL(10,2) NOT NULL,
    amount_paid DECIMAL(10,2) DEFAULT 0,
    
    -- Payment breakdown
    rent_amount DECIMAL(10,2) NOT NULL,
    maintenance_amount DECIMAL(10,2) DEFAULT 0,
    late_fee DECIMAL(10,2) DEFAULT 0,
    other_charges DECIMAL(10,2) DEFAULT 0,
    
    -- Payment status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'partial', 'paid', 'overdue', 'waived')),
    payment_method VARCHAR(50), -- upi, bank_transfer, cheque, cash
    
    -- Payment gateway integration
    payment_gateway_id VARCHAR(255),
    transaction_id VARCHAR(255),
    gateway_response JSONB,
    
    -- Timestamps
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rent_payments_lease ON rent_payments(lease_id);
CREATE INDEX idx_rent_payments_status ON rent_payments(status);
CREATE INDEX idx_rent_payments_due ON rent_payments(due_date);
```

### **6. Communication and Lead Management**

#### **contacts table** (CRM system)
```sql
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES users(id),
    
    -- Contact information
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    alternate_phone VARCHAR(20),
    
    -- Contact classification
    contact_type VARCHAR(50) NOT NULL CHECK (contact_type IN ('lead', 'client', 'prospect', 'past_client')),
    lead_source VARCHAR(100), -- website, referral, advertisement, etc.
    lead_quality VARCHAR(20) DEFAULT 'cold' CHECK (lead_quality IN ('hot', 'warm', 'cold')),
    
    -- Requirements
    looking_for VARCHAR(50), -- rent, buy, sell
    budget_min DECIMAL(10,2),
    budget_max DECIMAL(10,2),
    preferred_locations JSONB,
    property_requirements JSONB,
    timeline VARCHAR(50), -- immediate, 1_month, 3_months, 6_months
    
    -- Relationship status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'converted', 'lost', 'on_hold')),
    last_contact_date DATE,
    next_follow_up_date DATE,
    
    -- Notes and tags
    notes TEXT,
    tags TEXT[],
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contacts_agent ON contacts(agent_id);
CREATE INDEX idx_contacts_type ON contacts(contact_type, lead_quality);
CREATE INDEX idx_contacts_follow_up ON contacts(next_follow_up_date);
```

#### **contact_interactions table**
```sql
CREATE TABLE contact_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES users(id),
    
    -- Interaction details
    interaction_type VARCHAR(50) NOT NULL CHECK (interaction_type IN ('call', 'email', 'whatsapp', 'meeting', 'property_visit', 'follow_up')),
    interaction_date TIMESTAMP NOT NULL,
    duration_minutes INTEGER,
    
    -- Content
    subject VARCHAR(255),
    notes TEXT,
    outcome VARCHAR(100), -- interested, not_interested, callback_requested, etc.
    
    -- Follow-up
    next_action VARCHAR(255),
    next_action_date DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_interactions_contact ON contact_interactions(contact_id);
CREATE INDEX idx_interactions_date ON contact_interactions(interaction_date);
```

---

## 🗄️ MongoDB Collections

### **Property Media Collection**
```javascript
// Collection: property_media
{
  _id: ObjectId,
  property_id: "uuid-string",
  
  // Media information
  media_type: "image|video|360_tour|document|floor_plan",
  file_url: "https://storage.googleapis.com/...",
  thumbnail_url: "https://storage.googleapis.com/...",
  original_filename: "bedroom_photo.jpg",
  
  // File metadata
  file_size: 2048000, // bytes
  mime_type: "image/jpeg",
  dimensions: {
    width: 1920,
    height: 1080
  },
  
  // Capture information
  captured_at: ISODate,
  captured_by: "user_id",
  camera_info: {
    make: "Apple",
    model: "iPhone 14",
    location: {
      latitude: 12.9716,
      longitude: 77.5946
    }
  },
  
  // Classification and tags
  room_type: "bedroom|living_room|kitchen|bathroom|balcony|exterior",
  tags: ["furnished", "spacious", "natural_light"],
  is_primary: false, // main property image
  display_order: 1,
  
  // Verification
  is_verified: true,
  verification_status: "pending|approved|rejected",
  verified_by: "user_id",
  verified_at: ISODate,
  
  // Processing status
  processing_status: "pending|processing|completed|failed",
  processed_versions: {
    thumbnail: "url",
    medium: "url",
    large: "url"
  },
  
  // Access control
  visibility: "public|private|agent_only",
  access_permissions: ["owner_id", "agent_id"],
  
  created_at: ISODate,
  updated_at: ISODate
}
```

**🔍 Why MongoDB for media?**
- **Flexible schema**: Different media types have different metadata
- **Geographic data**: Better support for location-based queries
- **Scalability**: Better for high-volume media storage metadata
- **JSON structure**: Natural fit for nested metadata

### **Documents Collection**
```javascript
// Collection: documents
{
  _id: ObjectId,
  
  // Document identification
  entity_type: "property|lease|user|verification",
  entity_id: "uuid-string",
  document_type: "lease_agreement|kyc|income_proof|property_papers|verification_report",
  document_category: "legal|financial|identity|property|verification",
  
  // File information
  file_url: "https://storage.googleapis.com/...",
  original_filename: "lease_agreement_signed.pdf",
  file_size: 5120000,
  mime_type: "application/pdf",
  
  // Document metadata
  title: "Lease Agreement - Property XYZ",
  description: "Signed lease agreement for 2 BHK apartment",
  version: 1,
  is_latest_version: true,
  previous_version_id: ObjectId,
  
  // Security and encryption
  is_encrypted: true,
  encryption_key_id: "kms-key-id",
  access_level: "public|private|restricted",
  
  // Digital signature
  is_signed: true,
  signatures: [
    {
      signer_id: "user_id",
      signer_name: "John Doe",
      signed_at: ISODate,
      signature_url: "signature_image_url",
      ip_address: "192.168.1.1"
    }
  ],
  
  // Access control
  access_permissions: {
    read: ["user_id_1", "user_id_2"],
    write: ["user_id_1"],
    admin: ["user_id_admin"]
  },
  
  // Audit trail
  uploaded_by: "user_id",
  last_accessed_by: "user_id",
  last_accessed_at: ISODate,
  download_count: 15,
  
  // Compliance and retention
  retention_policy: "7_years",
  auto_delete_at: ISODate,
  compliance_tags: ["gdpr", "data_retention"],
  
  created_at: ISODate,
  updated_at: ISODate
}
```

### **Notifications Collection**
```javascript
// Collection: notifications
{
  _id: ObjectId,
  
  // Notification targeting
  user_id: "uuid-string",
  user_role: "owner|tenant|agent",
  
  // Notification content
  title: "New lease agreement ready for signature",
  message: "Your lease agreement for Property XYZ is ready for digital signature",
  notification_type: "lease_ready|payment_due|verification_complete|new_inquiry",
  priority: "low|medium|high|urgent",
  
  // Rich content
  data: {
    entity_type: "lease",
    entity_id: "lease_uuid",
    action_url: "/leases/uuid/sign",
    image_url: "notification_image_url"
  },
  
  // Delivery channels
  channels: {
    in_app: {
      status: "sent|delivered|read",
      delivered_at: ISODate,
      read_at: ISODate
    },
    email: {
      status: "pending|sent|delivered|failed",
      email_id: "email_service_id",
      delivered_at: ISODate,
      opened_at: ISODate,
      clicked_at: ISODate
    },
    sms: {
      status: "pending|sent|delivered|failed",
      sms_id: "sms_service_id",
      delivered_at: ISODate
    },
    whatsapp: {
      status: "pending|sent|delivered|read|failed",
      message_id: "whatsapp_message_id",
      delivered_at: ISODate,
      read_at: ISODate
    }
  },
  
  // Scheduling and automation
  scheduled_for: ISODate,
  is_scheduled: false,
  automation_rule_id: "rule_id",
  
  // User interaction
  is_read: false,
  read_at: ISODate,
  is_dismissed: false,
  dismissed_at: ISODate,
  action_taken: "clicked|dismissed|ignored",
  
  // Template information
  template_id: "template_uuid",
  template_version: 1,
  personalization_data: {
    property_address: "123 Main St",
    amount: 25000,
    due_date: "2024-01-15"
  },
  
  created_at: ISODate,
  updated_at: ISODate,
  expires_at: ISODate
}
```

---

## 📊 Redis Data Structures

### **Session Management**
```yaml
# Key pattern: session:{user_id}:{session_id}
session:123e4567-e89b-12d3-a456-426614174000:abc123
Value: {
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "role": "owner",
  "permissions": ["property:read", "property:write"],
  "device_info": {
    "type": "mobile",
    "os": "iOS"
  },
  "last_activity": 1640995200,
  "expires_at": 1640995200
}
TTL: 86400 (24 hours)
```

### **Property Search Cache**
```yaml
# Key pattern: search:properties:{hash_of_filters}
search:properties:city_bangalore_type_apartment_rent_20000_30000
Value: [
  "property_id_1",
  "property_id_2",
  "property_id_3"
]
TTL: 3600 (1 hour)

# Property details cache
property:123e4567-e89b-12d3-a456-426614174000
Value: {
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "2 BHK Apartment in Koramangala",
  "monthly_rent": 25000,
  "location": {
    "city": "Bangalore",
    "area": "Koramangala"
  },
  "cached_at": 1640995200
}
TTL: 1800 (30 minutes)
```

### **Real-time Notifications Queue**
```yaml
# List for notification queues
queue:notifications:email
queue:notifications:sms
queue:notifications:whatsapp

# Each queue item:
{
  "notification_id": "notification_uuid",
  "user_id": "user_uuid",
  "type": "payment_reminder",
  "priority": "high",
  "data": {...},
  "retry_count": 0,
  "created_at": 1640995200
}
```

### **Rate Limiting**
```yaml
# API rate limiting
rate_limit:api:{user_id}:{endpoint}
rate_limit:api:123e4567:property_search
Value: 95 (current count)
TTL: 3600 (resets every hour)

# OTP rate limiting
rate_limit:otp:{phone_number}
Value: 3 (attempts in last hour)
TTL: 3600
```

---

## 🔄 Data Relationships and Complex Queries

### **Property Search with Multiple Filters**
```sql
-- Complex property search query
WITH property_search AS (
  SELECT p.*,
         CASE 
           WHEN p.latitude IS NOT NULL AND p.longitude IS NOT NULL 
           THEN point(p.longitude, p.latitude) <-> point($user_lon, $user_lat)
           ELSE NULL 
         END as distance_km
  FROM properties p
  WHERE p.status = 'active'
    AND p.is_available = true
    AND p.city = $city
    AND p.property_type = $property_type
    AND p.monthly_rent BETWEEN $min_rent AND $max_rent
    AND p.bedrooms >= $min_bedrooms
    AND ($amenities = '{}' OR p.amenities @> $amenities)
),
property_with_ratings AS (
  SELECT ps.*,
         COALESCE(pr.avg_rating, 0) as property_rating,
         COALESCE(pr.review_count, 0) as review_count
  FROM property_search ps
  LEFT JOIN (
    SELECT property_id, 
           AVG(rating) as avg_rating,
           COUNT(*) as review_count
    FROM property_reviews 
    GROUP BY property_id
  ) pr ON ps.id = pr.property_id
)
SELECT * FROM property_with_ratings
ORDER BY 
  CASE WHEN $sort_by = 'rent_low' THEN monthly_rent END ASC,
  CASE WHEN $sort_by = 'rent_high' THEN monthly_rent END DESC,
  CASE WHEN $sort_by = 'distance' THEN distance_km END ASC,
  CASE WHEN $sort_by = 'rating' THEN property_rating END DESC,
  created_at DESC
LIMIT $limit OFFSET $offset;
```

### **Agent Performance Analytics**
```sql
-- Agent performance dashboard query
WITH agent_metrics AS (
  SELECT 
    ap.user_id,
    u.first_name || ' ' || u.last_name as agent_name,
    ap.total_deals_closed,
    ap.total_commission_earned,
    ap.average_rating,
    
    -- This month's performance
    COUNT(DISTINCT CASE WHEN l.created_at >= date_trunc('month', CURRENT_DATE) THEN l.id END) as deals_this_month,
    SUM(CASE WHEN l.created_at >= date_trunc('month', CURRENT_DATE) THEN l.brokerage_amount ELSE 0 END) as commission_this_month,
    
    -- Property verification metrics
    COUNT(DISTINCT pv.id) as total_verifications,
    AVG(pv.quality_score) as avg_verification_quality,
    
    -- Response time metrics
    AVG(EXTRACT(EPOCH FROM (ci.interaction_date - c.created_at))/3600) as avg_response_time_hours
    
  FROM agent_profiles ap
  JOIN users u ON ap.user_id = u.id
  LEFT JOIN leases l ON l.agent_id = ap.user_id
  LEFT JOIN property_verifications pv ON pv.agent_id = ap.user_id
  LEFT JOIN contacts c ON c.agent_id = ap.user_id
  LEFT JOIN contact_interactions ci ON ci.contact_id = c.id AND ci.interaction_type = 'call'
  
  WHERE ap.verification_status = 'verified'
  GROUP BY ap.user_id, u.first_name, u.last_name, ap.total_deals_closed, 
           ap.total_commission_earned, ap.average_rating
),
agent_rankings AS (
  SELECT *,
         ROW_NUMBER() OVER (ORDER BY deals_this_month DESC, commission_this_month DESC) as rank_this_month,
         ROW_NUMBER() OVER (ORDER BY total_deals_closed DESC) as rank_overall
  FROM agent_metrics
)
SELECT * FROM agent_rankings
ORDER BY rank_this_month;
```

---

## 🔧 Data Integrity and Business Rules

### **Database Constraints and Triggers**

#### **Automated Property Status Management**
```sql
-- Trigger to update property status when lease is created
CREATE OR REPLACE FUNCTION update_property_status_on_lease()
RETURNS TRIGGER AS $
BEGIN
  IF NEW.status = 'active' THEN
    UPDATE properties 
    SET status = 'rented', is_available = false
    WHERE id = NEW.property_id;
  ELSIF OLD.status = 'active' AND NEW.status IN ('terminated', 'expired') THEN
    UPDATE properties 
    SET status = 'active', is_available = true
    WHERE id = NEW.property_id;
  END IF;
  RETURN NEW;
END;
$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_property_status_on_lease
  AFTER INSERT OR UPDATE ON leases
  FOR EACH ROW
  EXECUTE FUNCTION update_property_status_on_lease();
```

#### **Rent Payment Due Date Calculation**
```sql
-- Function to automatically create rent payment records
CREATE OR REPLACE FUNCTION generate_rent_payments(lease_uuid UUID)
RETURNS VOID AS $
DECLARE
  lease_record RECORD;
  payment_date DATE;
  period_start DATE;
  period_end DATE;
BEGIN
  SELECT * INTO lease_record FROM leases WHERE id = lease_uuid;
  
  payment_date := lease_record.lease_start_date;
  
  WHILE payment_date <= lease_record.lease_end_date LOOP
    period_start := payment_date;
    period_end := payment_date + INTERVAL '1 month' - INTERVAL '1 day';
    
    INSERT INTO rent_payments (
      lease_id, tenant_id, owner_id, payment_period_start, 
      payment_period_end, due_date, amount_due, rent_amount
    ) VALUES (
      lease_record.id,
      lease_record.tenant_id,
      lease_record.owner_id,
      period_start,
      period_end,
      payment_date,
      lease_record.monthly_rent + lease_record.maintenance_charge,
      lease_record.monthly_rent
    );
    
    payment_date := payment_date + INTERVAL '1 month';
  END LOOP;
END;
$ LANGUAGE plpgsql;
```

### **Data Validation Rules**

#### **Business Logic Constraints**
```sql
-- Ensure lease dates are logical
ALTER TABLE leases ADD CONSTRAINT check_lease_dates 
  CHECK (lease_end_date > lease_start_date);

-- Ensure security deposit is reasonable (max 12 months rent)
ALTER TABLE leases ADD CONSTRAINT check_security_deposit 
  CHECK (security_deposit <= monthly_rent * 12);

-- Ensure property coordinates are in India (approximate bounds)
ALTER TABLE properties ADD CONSTRAINT check_india_coordinates
  CHECK (
    (latitude IS NULL AND longitude IS NULL) OR
    (latitude BETWEEN 6.0 AND 37.6 AND longitude BETWEEN 68.7 AND 97.25)
  );

-- Ensure agent commission is reasonable
ALTER TABLE agent_profiles ADD CONSTRAINT check_commission_rate
  CHECK (commission_rate >= 0 AND commission_rate <= 10);
```

---

## 📋 Data Migration and Seeding Strategy

### **Initial Data Seeding**
```sql
-- Cities and areas master data
CREATE TABLE master_cities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  city_name VARCHAR(100) NOT NULL,
  state_name VARCHAR(100) NOT NULL,
  state_code VARCHAR(10),
  country VARCHAR(100) DEFAULT 'India',
  latitude DECIMAL(10,8),
  longitude DECIMAL(11,8),
  is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE master_areas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  city_id UUID REFERENCES master_cities(id),
  area_name VARCHAR(255) NOT NULL,
  pincode VARCHAR(10),
  area_type VARCHAR(50), -- residential, commercial, mixed
  latitude DECIMAL(10,8),
  longitude DECIMAL(11,8),
  is_popular BOOLEAN DEFAULT FALSE
);

-- Property amenities master data
CREATE TABLE master_amenities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  amenity_name VARCHAR(255) NOT NULL,
  amenity_category VARCHAR(100), -- security, fitness, convenience, entertainment
  icon_name VARCHAR(100),
  is_premium BOOLEAN DEFAULT FALSE,
  typical_cost DECIMAL(10,2)
);
```

### **Sample Data Insertion**
```sql
-- Insert major Indian cities
INSERT INTO master_cities (city_name, state_name, state_code, latitude, longitude) VALUES
('Bangalore', 'Karnataka', 'KA', 12.9716, 77.5946),
('Mumbai', 'Maharashtra', 'MH', 19.0760, 72.8777),
('Delhi', 'Delhi', 'DL', 28.6139, 77.2090),
('Chennai', 'Tamil Nadu', 'TN', 13.0827, 80.2707),
('Hyderabad', 'Telangana', 'TS', 17.3850, 78.4867),
('Pune', 'Maharashtra', 'MH', 18.5204, 73.8567);

-- Insert popular areas in Bangalore
INSERT INTO master_areas (city_id, area_name, pincode, area_type, is_popular) 
SELECT c.id, area_name, pincode, 'residential', true
FROM master_cities c,
(VALUES 
  ('Koramangala', '560034'),
  ('Indiranagar', '560038'),
  ('HSR Layout', '560102'),
  ('BTM Layout', '560076'),
  ('Electronic City', '560100'),
  ('Whitefield', '560066')
) AS areas(area_name, pincode)
WHERE c.city_name = 'Bangalore';

-- Insert common amenities
INSERT INTO master_amenities (amenity_name, amenity_category, is_premium) VALUES
('Parking', 'convenience', false),
('Security', 'security', false),
('Elevator', 'convenience', false),
('Power Backup', 'convenience', false),
('Swimming Pool', 'fitness', true),
('Gym', 'fitness', true),
('Club House', 'entertainment', true),
('Garden', 'convenience', false),
('Play Area', 'entertainment', false),
('CCTV', 'security', false);
```

---

## 🚀 Performance Optimization Strategies

### **Database Indexing Strategy**
```sql
-- Composite indexes for common query patterns
CREATE INDEX idx_properties_search_combo ON properties(city, property_type, monthly_rent, bedrooms, status, is_available);
CREATE INDEX idx_properties_location_price ON properties(city, monthly_rent) WHERE status = 'active';

-- Partial indexes for active data
CREATE INDEX idx_active_properties ON properties(created_at DESC) WHERE status = 'active' AND is_available = true;
CREATE INDEX idx_verified_agents ON agent_profiles(average_rating DESC) WHERE verification_status = 'verified';

-- JSON indexes for flexible queries
CREATE INDEX idx_property_amenities_gin ON properties USING GIN(amenities);
CREATE INDEX idx_notification_data ON notifications USING GIN(data) WHERE (data IS NOT NULL);
```

### **Caching Strategy**
```yaml
Hot Data (Redis TTL: 30 minutes):
  - Active property listings
  - User session data
  - Search results for popular filters
  - Agent performance metrics

Warm Data (Redis TTL: 4 hours):
  - Property details with media
  - User profile information
  - Master data (cities, amenities)
  - Notification templates

Cold Data (Database only):
  - Historical transactions
  - Audit logs
  - Archived properties
  - Old notifications
```

---

## 🔐 Security and Privacy Considerations

### **Data Encryption and Masking**
```sql
-- Sensitive data encryption functions
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(input_text TEXT)
RETURNS TEXT AS $
BEGIN
  -- In production, use proper encryption key management
  RETURN encode(encrypt(input_text::bytea, 'encryption_key', 'aes'), 'base64');
END;
$ LANGUAGE plpgsql;

-- Data masking for non-production environments
CREATE OR REPLACE FUNCTION mask_phone_number(phone_number VARCHAR)
RETURNS VARCHAR AS $
BEGIN
  RETURN CASE 
    WHEN LENGTH(phone_number) >= 10 
    THEN SUBSTRING(phone_number, 1, 2) || 'XXXXX' || SUBSTRING(phone_number, LENGTH(phone_number)-2)
    ELSE 'XXXXX'
  END;
END;
$ LANGUAGE plpgsql;
```

### **Data Retention Policies**
```sql
-- Automatic cleanup of old data
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS VOID AS $
BEGIN
  -- Delete old OTP records (older than 24 hours)
  DELETE FROM otp_verifications WHERE created_at < NOW() - INTERVAL '24 hours';
  
  -- Archive old notifications (older than 6 months)
  INSERT INTO notifications_archive SELECT * FROM notifications 
  WHERE created_at < NOW() - INTERVAL '6 months';
  
  DELETE FROM notifications WHERE created_at < NOW() - INTERVAL '6 months';
  
  -- Delete inactive user sessions
  DELETE FROM user_sessions WHERE expires_at < NOW() OR last_used_at < NOW() - INTERVAL '30 days';
END;
$ LANGUAGE plpgsql;

-- Schedule cleanup job
SELECT cron.schedule('cleanup-old-data', '0 2 * * *', 'SELECT cleanup_old_data();');
```

---

## 📊 Analytics and Reporting Data Models

### **Business Intelligence Views**
```sql
-- Property performance analytics
CREATE MATERIALIZED VIEW property_analytics AS
SELECT 
  p.id as property_id,
  p.city,
  p.property_type,
  p.monthly_rent,
  p.bedrooms,
  
  -- Listing performance
  EXTRACT(DAYS FROM (COALESCE(l.lease_start_date, CURRENT_DATE) - p.created_at)) as days_to_rent,
  
  -- Financial metrics
  CASE WHEN l.id IS NOT NULL THEN p.monthly_rent * 12 ELSE 0 END as annual_rental_value,
  
  -- Engagement metrics
  COALESCE(views.view_count, 0) as total_views,
  COALESCE(inquiries.inquiry_count, 0) as total_inquiries,
  
  -- Current status
  p.status,
  p.verification_status,
  
  p.created_at as listed_date,
  l.lease_start_date as rented_date
  
FROM properties p
LEFT JOIN leases l ON l.property_id = p.id AND l.status = 'active'
LEFT JOIN (
  SELECT property_id, COUNT(*) as view_count 
  FROM property_views 
  GROUP BY property_id
) views ON views.property_id = p.id
LEFT JOIN (
  SELECT property_id, COUNT(*) as inquiry_count 
  FROM property_inquiries 
  GROUP BY property_id
) inquiries ON inquiries.property_id = p.id;

-- Refresh analytics daily
SELECT cron.schedule('refresh-property-analytics', '0 6 * * *', 'REFRESH MATERIALIZED VIEW property_analytics;');
```

---

## 🎯 Key Design Decisions Summary

### **Why This Complex Data Model?**

1. **Scalability**: Designed to handle millions of properties and users
2. **Compliance**: Built-in audit trails, data retention, and privacy controls
3. **Performance**: Strategic indexing and caching for common queries
4. **Flexibility**: JSONB fields allow for evolving requirements without schema changes
5. **Business Logic**: Automated workflows and business rule enforcement
6. **Multi-tenancy**: Clean separation between different user types and their data
7. **Real-time Features**: Redis integration for caching and real-time notifications
8. **Analytics Ready**: Built-in metrics and reporting capabilities

### **Non-Trivial Design Choices Explained**

1. **Separate Profile Tables**: Role-specific data without NULL columns in main user table
2. **JSONB Usage**: Flexible schemas for amenities, preferences, and metadata
3. **Geographic Indexing**: GIST indexes for location-based property searches
4. **Verification Workflow**: Quality assurance critical for real estate platform
5. **Digital Signatures**: Legal compliance for rental agreements in India
6. **Multi-channel Notifications**: Users expect communication across platforms
7. **Performance Metrics**: Agent ratings and analytics drive business decisions
8. **Audit Trails**: Regulatory compliance and dispute resolution

This data model provides a solid foundation for your Alter8 platform while maintaining flexibility for future enhancements! 🚀